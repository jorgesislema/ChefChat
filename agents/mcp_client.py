"""Módulo MCP Client para administrar plantillas y operaciones de documentos de Office."""

import os
import pythoncom  # type: ignore[import-untyped]
from typing import Any, Dict, Type
from core.config import ConfigManager

try:
    PythonComError: Type[BaseException] = pythoncom.com_error  # type: ignore[assignment]
except AttributeError:
    PythonComError = Exception
from core.models import AccionOffice


PLANTILLAS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "plantillas")


class MCPClient:
    """Cliente para administrar operaciones MCP y plantillas de documentos de Office."""

    def __init__(self) -> None:
        self.sandbox_path = ConfigManager.get_sandbox_path()
        self._word_app = None
        self._excel_app = None
        self._powerpoint_app = None
        os.makedirs(PLANTILLAS_DIR, exist_ok=True)

    def _validar_ruta_sandbox(self, ruta_archivo: str) -> bool:
        return ConfigManager.is_path_in_sandbox(ruta_archivo)

    def conectar_servidor(self, ruta_mcp: str) -> bool:
        """Conecta al servidor MCP si la ruta es válida dentro del sandbox."""
        if not ruta_mcp:
            return False
        return self._validar_ruta_sandbox(ruta_mcp)

    def listar_plantillas(self) -> list:
        archivos = []
        for f in os.listdir(PLANTILLAS_DIR):
            if f.endswith((".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls")):
                archivos.append(f)
        return archivos

    def _initialize_com(self) -> None:
        try:
            coinitialize = pythoncom.CoInitialize
            if callable(coinitialize):
                coinitialize()
        except (AttributeError, TypeError, PythonComError):
            pass

    def _get_word_app(self):
        if self._word_app is None:
            from win32com.client import Dispatch
            self._initialize_com()
            self._word_app = Dispatch("Word.Application")
            self._word_app.Visible = True
        return self._word_app

    def _get_excel_app(self):
        if self._excel_app is None:
            from win32com.client import Dispatch
            self._initialize_com()
            self._excel_app = Dispatch("Excel.Application")
            self._excel_app.Visible = True
        return self._excel_app

    def _get_powerpoint_app(self):
        if self._powerpoint_app is None:
            from win32com.client import Dispatch
            self._initialize_com()
            self._powerpoint_app = Dispatch("PowerPoint.Application")
            self._powerpoint_app.Visible = True
        return self._powerpoint_app

    def ejecutar_herramienta(self, accion: AccionOffice) -> Dict[str, Any]:
        if accion.operacion == "plantilla":
            return self._procesar_plantilla(accion)
        if accion.herramienta == "excel":
            return self._procesar_excel(accion)
        elif accion.herramienta == "word":
            return self._procesar_word(accion)
        elif accion.herramienta == "powerpoint":
            return self._procesar_powerpoint(accion)
        return {"status": "error", "mensaje": f"Herramienta '{accion.herramienta}' no soportada"}

    def _procesar_plantilla(self, accion: AccionOffice) -> Dict[str, Any]:
        nombre = accion.payload.get("plantilla", "")
        if not nombre:
            return {"status": "error", "mensaje": "Nombre de plantilla requerido"}

        plantilla_path = os.path.join(PLANTILLAS_DIR, nombre)
        if not os.path.exists(plantilla_path):
            disponibles = self.listar_plantillas()
            return {"status": "error", "mensaje": f"Plantilla '{nombre}' no encontrada. Disponibles: {', '.join(disponibles) if disponibles else 'ninguna'}"}

        datos = accion.payload.get("datos", {})

        if nombre.endswith((".docx", ".doc")):
            return self._aplicar_plantilla_word(plantilla_path, datos)
        elif nombre.endswith((".pptx", ".ppt")):
            return self._aplicar_plantilla_powerpoint(plantilla_path, datos)
        else:
            return {"status": "error", "mensaje": "Solo se soportan plantillas Word (.docx) y PowerPoint (.pptx)"}

    def _reemplazar_placeholders(self, contenido: str, datos: dict) -> str:
        for key, value in datos.items():
            contenido = contenido.replace("{{" + key + "}}", str(value))
        return contenido

    def _aplicar_plantilla_word(self, plantilla_path: str, datos: dict) -> Dict[str, Any]:
        try:
            word = self._get_word_app()
            doc = word.Documents.Open(plantilla_path)

            find = word.Selection.Find
            for key, value in datos.items():
                placeholder = "{{" + key + "}}"
                word.Selection.HomeKey(Unit=6)
                find.ClearFormatting()
                find.Text = placeholder
                find.Replacement.ClearFormatting()
                find.Replacement.Text = str(value)
                find.Execute(Replace=2)

            doc.Activate()
            return {"status": "ok", "mensaje": f"Plantilla '{os.path.basename(plantilla_path)}' aplicada en Word"}
        except (PythonComError, AttributeError, ValueError, TypeError) as e:
            return {"status": "error", "mensaje": f"Error al aplicar plantilla Word: {str(e)}"}

    def _aplicar_plantilla_powerpoint(self, plantilla_path: str, datos: dict) -> Dict[str, Any]:
        try:
            ppt = self._get_powerpoint_app()
            pres = ppt.Presentations.Open(plantilla_path)

            for slide in pres.Slides:
                for shape in slide.Shapes:
                    if shape.HasTextFrame:
                        for para in shape.TextFrame.TextRange.Paragraphs:
                            texto = para.Text
                            nuevo = self._reemplazar_placeholders(texto, datos)
                            if nuevo != texto:
                                para.Text = nuevo

            pres.Activate()
            return {"status": "ok", "mensaje": f"Plantilla '{os.path.basename(plantilla_path)}' aplicada en PowerPoint"}
        except (PythonComError, AttributeError, ValueError, TypeError) as e:
            return {"status": "error", "mensaje": f"Error al aplicar plantilla PowerPoint: {str(e)}"}

    def _procesar_excel(self, accion: AccionOffice) -> Dict[str, Any]:
        if accion.operacion == "enviar":
            return self._enviar_a_excel(accion)
        elif accion.operacion == "crear":
            if not self._validar_ruta_sandbox(accion.ruta_archivo):
                raise PermissionError("Ruta fuera del Sandbox")
            os.makedirs(os.path.dirname(accion.ruta_archivo), exist_ok=True)
            import csv
            with open(accion.ruta_archivo.replace(".xlsx", ".csv"), "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                for row in accion.payload.get("datos", []):
                    writer.writerow(row)
            return {"status": "ok", "mensaje": f"Archivo creado en {accion.ruta_archivo}"}
        elif accion.operacion == "leer":
            # Operación de lectura - retorna OK sin hacer nada (placeholder para futura implementación)
            if not self._validar_ruta_sandbox(accion.ruta_archivo):
                raise PermissionError("Ruta fuera del Sandbox")
            return {"status": "ok", "mensaje": "Operación de lectura completada (placeholder)"}
        return {"status": "error", "mensaje": f"Operación '{accion.operacion}' no soportada"}

    def _procesar_word(self, accion: AccionOffice) -> Dict[str, Any]:
        if accion.operacion == "enviar":
            return self._enviar_a_word(accion)
        elif accion.operacion == "crear":
            if not self._validar_ruta_sandbox(accion.ruta_archivo):
                raise PermissionError("Ruta fuera del Sandbox")
            os.makedirs(os.path.dirname(accion.ruta_archivo), exist_ok=True)
            contenido = accion.payload.get("contenido", "")
            with open(accion.ruta_archivo.replace(".docx", ".txt"), "w", encoding="utf-8") as f:
                f.write(contenido)
            return {"status": "ok", "mensaje": f"Documento creado en {accion.ruta_archivo}"}
        return {"status": "error"}

    def _procesar_powerpoint(self, accion: AccionOffice) -> Dict[str, Any]:
        if accion.operacion == "enviar":
            return self._enviar_a_powerpoint(accion)
        elif accion.operacion == "crear":
            if not self._validar_ruta_sandbox(accion.ruta_archivo):
                raise PermissionError("Ruta fuera del Sandbox")
            os.makedirs(os.path.dirname(accion.ruta_archivo), exist_ok=True)
            contenido = accion.payload.get("contenido", "")
            with open(accion.ruta_archivo.replace(".pptx", ".txt"), "w", encoding="utf-8") as f:
                f.write(contenido)
            return {"status": "ok", "mensaje": f"Presentacion base creada en {accion.ruta_archivo}"}
        return {"status": "error"}

    def _enviar_a_excel(self, accion: AccionOffice) -> Dict[str, Any]:
        try:
            excel = self._get_excel_app()
            wb = excel.ActiveWorkbook
            if not wb:
                wb = excel.Workbooks.Add()
            ws = wb.ActiveSheet

            datos = accion.payload.get("datos", [])
            insertar_en = accion.payload.get("insertar_en", "A1")

            if not datos:
                return {"status": "error", "mensaje": "No hay datos para enviar"}

            if isinstance(datos, list) and all(isinstance(r, list) for r in datos):
                start_col = ord(insertar_en[0].upper()) - ord('A') + 1
                start_row = int(insertar_en[1:]) if len(insertar_en) > 1 else 1
                for i, row in enumerate(datos):
                    for j, val in enumerate(row):
                        cell = ws.Cells(start_row + i, start_col + j)
                        cell.Value = str(val) if val is not None else ""
                rng = ws.Range(ws.Cells(start_row, start_col), ws.Cells(start_row + len(datos) - 1, start_col + len(datos[0]) - 1))
                rng.EntireColumn.AutoFit()
            elif isinstance(datos, dict):
                start_col = ord(insertar_en[0].upper()) - ord('A') + 1
                start_row = int(insertar_en[1:]) if len(insertar_en) > 1 else 1
                for j, (key, value) in enumerate(datos.items()):
                    ws.Cells(start_row, start_col + j).Value = str(key)
                    if isinstance(value, list):
                        for i, v in enumerate(value):
                            ws.Cells(start_row + 1 + i, start_col + j).Value = str(v) if v is not None else ""
                    else:
                        ws.Cells(start_row + 1, start_col + j).Value = str(value) if value is not None else ""
                rng = ws.Range(ws.Cells(start_row, start_col), ws.Cells(start_row + 1, start_col + len(datos) - 1))
                rng.EntireColumn.AutoFit()

            return {"status": "ok", "mensaje": f"Datos enviados a Excel en {insertar_en}"}
        except (PythonComError, AttributeError, ValueError, TypeError) as e:
            return {"status": "error", "mensaje": f"Error al enviar a Excel: {str(e)}"}

    def _enviar_a_word(self, accion: AccionOffice) -> Dict[str, Any]:
        try:
            word = self._get_word_app()
            doc = word.ActiveDocument
            if not doc:
                doc = word.Documents.Add()

            selection = word.Selection
            fmt = accion.payload.get("formato", {})

            fuente = fmt.get("font_name", "Calibri")
            color = fmt.get("font_color", "")
            tamano_base = fmt.get("font_size", 11)
            alineacion = fmt.get("alignment", "left").lower()
            imagen_path = fmt.get("imagen", "")

            align_map = {"left": 0, "center": 1, "right": 2, "justify": 3}
            selection.ParagraphFormat.Alignment = align_map.get(alineacion, 0)

            if imagen_path and os.path.exists(imagen_path):
                selection.InlineShapes.AddPicture(imagen_path)
                selection.TypeParagraph()

            titulo = fmt.get("titulo", "")
            if titulo:
                selection.Font.Name = fmt.get("titulo_font", fuente)
                selection.Font.Bold = True
                selection.Font.Size = fmt.get("titulo_size", 18)
                if color:
                    try:
                        selection.Font.Color = int(color.replace("#", ""), 16) if color.startswith("#") else int(color)
                    except (ValueError, TypeError):
                        pass
                selection.TypeText(titulo)
                selection.Font.Bold = False
                selection.Font.Size = tamano_base
                selection.TypeParagraph()

            contenido = accion.payload.get("contenido", "")
            for linea in contenido.split("\n"):
                linea = linea.strip()
                if not linea:
                    selection.TypeParagraph()
                    continue
                selection.Font.Name = fuente
                selection.Font.Size = tamano_base
                if color:
                    try:
                        selection.Font.Color = int(color.replace("#", ""), 16) if color.startswith("#") else int(color)
                    except (ValueError, TypeError):
                        pass
                if linea.startswith("**") and linea.endswith("**"):
                    selection.Font.Bold = True
                    selection.Font.Size = tamano_base + 2
                    selection.TypeText(linea.strip("*"))
                    selection.Font.Bold = False
                    selection.Font.Size = tamano_base
                elif linea.startswith("- "):
                    selection.TypeText(linea)
                elif linea.startswith("# "):
                    selection.Font.Bold = True
                    selection.Font.Size = tamano_base + 6
                    selection.TypeText(linea[2:])
                    selection.Font.Bold = False
                    selection.Font.Size = tamano_base
                else:
                    selection.TypeText(linea)
                selection.TypeParagraph()

            return {"status": "ok", "mensaje": "Contenido enviado a Word"}
        except (PythonComError, AttributeError, ValueError, TypeError) as e:
            return {"status": "error", "mensaje": f"Error al enviar a Word: {str(e)}"}

    def _enviar_a_powerpoint(self, accion: AccionOffice) -> Dict[str, Any]:
        try:
            ppt = self._get_powerpoint_app()
            pres = ppt.ActivePresentation
            if not pres:
                pres = ppt.Presentations.Add()

            contenido = accion.payload.get("contenido", "")
            if not contenido:
                return {"status": "error", "mensaje": "No hay contenido para enviar"}

            fmt = accion.payload.get("formato", {})
            slide = pres.Slides.Add(pres.Slides.Count + 1, 1)

            titulo = fmt.get("titulo", "")
            if titulo:
                slide.Shapes.Title.TextFrame.TextRange.Text = titulo

            # Enviar contenido - verificar si existe el shape de cuerpo
            try:
                body_shape = slide.Shapes[2]
                body_shape.TextFrame.TextRange.Text = contenido
            except (PythonComError, IndexError, AttributeError):
                # Si no existe, agregar un nuevo shape de texto
                slide.Shapes.AddTextbox(1, 50, 100, 600, 400).TextFrame.TextRange.Text = contenido

            return {"status": "ok", "mensaje": f"Contenido enviado a PowerPoint (diapositiva {pres.Slides.Count})"}
        except (PythonComError, AttributeError, ValueError, TypeError) as e:
            return {"status": "error", "mensaje": f"Error al enviar a PowerPoint: {str(e)}"}

    def close(self):
        self._word_app = None
        self._excel_app = None
        self._powerpoint_app = None
