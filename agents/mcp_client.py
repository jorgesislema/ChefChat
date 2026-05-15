import os
from typing import Dict, Any
from core.config import ConfigManager
from core.models import AccionOffice


class MCPClient:
    def __init__(self) -> None:
        self.sandbox_path = ConfigManager.get_sandbox_path()

    def _validar_ruta_sandbox(self, ruta_archivo: str) -> bool:
        return ConfigManager.is_path_in_sandbox(ruta_archivo)

    def conectar_servidor(self, ruta_mcp: str) -> bool:
        return True

    def ejecutar_herramienta(self, accion: AccionOffice) -> Dict[str, Any]:
        if accion.requiere_hitl and accion.operacion in ("escribir", "crear"):
            if not self._validar_ruta_sandbox(accion.ruta_archivo):
                raise PermissionError(
                    f"Ruta no esta en Sandbox. Debe comenzar con {self.sandbox_path}"
                )
        if accion.herramienta == "excel":
            return self._procesar_excel(accion)
        elif accion.herramienta == "word":
            return self._procesar_word(accion)
        return {"status": "error", "mensaje": "Herramienta no soportada"}

    def _procesar_excel(self, accion: AccionOffice) -> Dict[str, Any]:
        if accion.operacion == "leer":
            return {"status": "ok", "datos": []}
        elif accion.operacion in ("escribir", "crear"):
            if not self._validar_ruta_sandbox(accion.ruta_archivo):
                raise PermissionError("Ruta fuera del Sandbox")
            import csv

            os.makedirs(os.path.dirname(accion.ruta_archivo), exist_ok=True)
            with open(accion.ruta_archivo.replace(".xlsx", ".csv"), "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if "datos" in accion.payload:
                    for row in accion.payload["datos"]:
                        writer.writerow(row)
            return {
                "status": "ok",
                "mensaje": f"Archivo creado en {accion.ruta_archivo}",
            }
        return {"status": "error"}

    def _procesar_word(self, accion: AccionOffice) -> Dict[str, Any]:
        if accion.operacion == "leer":
            return {"status": "ok", "contenido": ""}
        elif accion.operacion in ("escribir", "crear"):
            if not self._validar_ruta_sandbox(accion.ruta_archivo):
                raise PermissionError("Ruta fuera del Sandbox")
            os.makedirs(os.path.dirname(accion.ruta_archivo), exist_ok=True)
            contenido = accion.payload.get("contenido", "")
            with open(accion.ruta_archivo.replace(".docx", ".txt"), "w", encoding="utf-8") as f:
                f.write(contenido)
            return {
                "status": "ok",
                "mensaje": f"Documento creado en {accion.ruta_archivo}",
            }
        return {"status": "error"}