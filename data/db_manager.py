import sqlite3
import json
from datetime import datetime
from typing import List, Optional
from contextlib import contextmanager
from core.models import Receta, Evento, Ingrediente


class DatabaseManager:
    def __init__(self, db_path: str = "chefchat_memory.db") -> None:
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS historial_chat (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    rol TEXT NOT NULL,
                    contenido TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS eventos (
                    id_evento TEXT PRIMARY KEY,
                    tipo_evento TEXT NOT NULL,
                    fecha TEXT NOT NULL,
                    presupuesto REAL NOT NULL,
                    estado_aprobacion TEXT DEFAULT 'pendiente'
                )
            """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS recetas (
                    id_receta TEXT PRIMARY KEY,
                    nombre TEXT NOT NULL,
                    ingredientes TEXT NOT NULL,
                    alergenos TEXT NOT NULL,
                    costo_estimado REAL NOT NULL
                )
            """
            )
            conn.commit()

    def save_message(self, session_id: str, rol: str, contenido: str) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO historial_chat (session_id, rol, contenido) VALUES (?, ?, ?)",
                (session_id, rol, contenido),
            )
            conn.commit()

    def get_historial(self, session_id: str, limit: int = 50) -> List[dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT rol, contenido, timestamp
                FROM historial_chat
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (session_id, limit),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in reversed(rows)]

    def save_receta(self, receta: Receta) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO recetas (id_receta, nombre, ingredientes, alergenos, costo_estimado)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    receta.id_receta,
                    receta.nombre,
                    json.dumps([i.model_dump() for i in receta.ingredientes]),
                    json.dumps(receta.alergenos),
                    receta.costo_estimado,
                ),
            )
            conn.commit()

    def get_receta(self, id_receta: str) -> Optional[Receta]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM recetas WHERE id_receta = ?", (id_receta,))
            row = cursor.fetchone()
            if row:
                ingredientes_data = json.loads(row["ingredientes"])
                return Receta(
                    id_receta=row["id_receta"],
                    nombre=row["nombre"],
                    ingredientes=[Ingrediente(**i) for i in ingredientes_data],
                    alergenos=json.loads(row["alergenos"]),
                    costo_estimado=row["costo_estimado"],
                )
            return None

    def get_all_recetas(self) -> List[Receta]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM recetas")
            rows = cursor.fetchall()
            recetas = []
            for row in rows:
                ingredientes_data = json.loads(row["ingredientes"])
                recetas.append(
                    Receta(
                        id_receta=row["id_receta"],
                        nombre=row["nombre"],
                        ingredientes=[Ingrediente(**i) for i in ingredientes_data],
                        alergenos=json.loads(row["alergenos"]),
                        costo_estimado=row["costo_estimado"],
                    )
                )
            return recetas

    def save_evento(self, evento: Evento) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO eventos (id_evento, tipo_evento, fecha, presupuesto, estado_aprobacion)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    evento.id_evento,
                    evento.tipo_evento,
                    evento.fecha,
                    evento.presupuesto,
                    evento.estado_aprobacion,
                ),
            )
            conn.commit()

    def get_evento(self, id_evento: str) -> Optional[Evento]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM eventos WHERE id_evento = ?", (id_evento,))
            row = cursor.fetchone()
            if row:
                return Evento(
                    id_evento=row["id_evento"],
                    tipo_evento=row["tipo_evento"],
                    fecha=row["fecha"],
                    presupuesto=row["presupuesto"],
                    estado_aprobacion=row["estado_aprobacion"],
                )
            return None

    def get_eventos(self, limit: int = 50) -> List[Evento]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM eventos ORDER BY fecha DESC LIMIT ?", (limit,)
            )
            rows = cursor.fetchall()
            return [
                Evento(
                    id_evento=row["id_evento"],
                    tipo_evento=row["tipo_evento"],
                    fecha=row["fecha"],
                    presupuesto=row["presupuesto"],
                    estado_aprobacion=row["estado_aprobacion"],
                )
                for row in rows
            ]