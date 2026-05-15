"""
Herramientas Operativas para ChefChat Pro - LangChain Tools

Este módulo implementa las 5 herramientas principales que el LLM puede
ejecutar mediante Tool Calling. Cada herramienta está tipada con Pydantic V2
para validación estricta de entradas.
"""

from typing import List, Dict, Any, Optional
from langchain_core.tools import Tool
from data.db_manager import DatabaseManager
from core.models import (
    CaducidadInput, UsoInventarioInput, EscalarRecetaInput,
    IncidenciaInput, AnalisisRentabilidadOutput
)


def crear_herramientas_operativas(db: DatabaseManager) -> List[Tool]:
    """
    Crea y configura las 5 herramientas operativas para LangChain.
    
    Args:
        db: Instancia de DatabaseManager inicializada.
        
    Returns:
        List[Tool]: Lista de herramientas configuradas.
    """
    
    def _obtener_ingredientes_por_caducar(dias_limite: int) -> str:
        """
        Consulta ingredientes que caducarán en los próximos días.
        
        Usa la Vista_Caducidad para identificar productos cercanos a vencer
        y aplicar política FEFO (First Expired, First Out).
        
        Args:
            dias_limite: Número de días para la consulta (1-90).
            
        Returns:
            str: JSON con productos por caducar ordenados por urgencia.
        """
        try:
            input_data = CaducidadInput(dias_limite=dias_limite)
            resultados = db.obtener_ingredientes_por_caducar(input_data.dias_limite)
            
            if not resultados:
                return f"No hay ingredientes por caducar en los próximos {dias_limite} días."
            
            salida = []
            for item in resultados:
                salida.append({
                    "producto": item.producto_nombre,
                    "categoria": item.categoria,
                    "cantidad_disponible": f"{item.cantidad} {item.unidad}",
                    "fecha_caducidad": item.fecha_caducidad_efectiva.isoformat(),
                    "dias_restantes": item.dias_restantes,
                    "prioridad": "CRÍTICA" if item.dias_restantes <= 2 else "ALTA" if item.dias_restantes <= 5 else "MEDIA"
                })
            
            return f"Ingredientes por caducar ({len(salida)} encontrados):\n" + "\n".join(
                f"- {i['producto']}: {i['dias_restantes']} días restantes ({i['prioridad']})" 
                for i in salida
            )
            
        except Exception as e:
            return f"Error al consultar caducidad: {str(e)}"

    def _registrar_uso_inventario(nombre_item: str, cantidad_usada: float) -> str:
        """
        Registra el uso de un ingrediente del inventario.
        
        Aplica política FEFO descontando primero del lote más antiguo.
        
        Args:
            nombre_item: Nombre del producto (ej. "Fresa", "Pollo").
            cantidad_usada: Cantidad a descontar (debe ser > 0).
            
        Returns:
            str: Confirmación del uso registrado o error.
        """
        try:
            input_data = UsoInventarioInput(
                nombre_item=nombre_item,
                cantidad_usada=cantidad_usada
            )
            resultado = db.registrar_uso_inventario(
                input_data.nombre_item,
                input_data.cantidad_usada
            )
            return f"✅ {resultado}"
            
        except ValueError as e:
            return f"⚠️ {str(e)}"
        except Exception as e:
            return f"❌ Error: {str(e)}"

    def _escalar_receta(receta_id: int, comensales: int) -> str:
        """
        Escala matemáticamente una receta para nuevo número de comensales.
        
        Multiplica todos los ingredientes por el factor de escala:
        factor = comensales_nuevos / comensales_originales
        
        Args:
            receta_id: ID de la receta en la base de datos.
            comensales: Número de comensales deseado.
            
        Returns:
            str: Receta escalada con ingredientes ajustados.
        """
        try:
            input_data = EscalarRecetaInput(
                receta_id=receta_id,
                comensales=comensales
            )
            receta = db.escalar_receta(input_data.receta_id, input_data.comensales)
            
            salida = [
                f"📖 Receta: {receta['nombre']}",
                f"👥 Escala: {receta['comensales_originales']} → {receta['comensales_nuevos']} comensales",
                f"🔢 Factor: {receta['factor_escala']}x",
                "",
                "🥗 Ingredientes escalados:"
            ]
            
            for ing in receta["ingredientes"]:
                salida.append(f"  - {ing['nombre']}: {ing['cantidad']} {ing['unidad']}")
            
            salida.append(f"\n💰 Costo estimado: ${receta['costo_produccion_estimado']:.2f}")
            
            return "\n".join(salida)
            
        except ValueError as e:
            return f"⚠️ {str(e)}"
        except Exception as e:
            return f"❌ Error: {str(e)}"

    def _registrar_incidencia(categoria: str, descripcion: str) -> str:
        """
        Registra una incidencia en la bitácora diaria.
        
        Categorías válidas: Operativa, Calidad, Inventario, Venta,
        Mantenimiento, Personal, Proveedor, Otro.
        
        Args:
            categoria: Categoría de la incidencia.
            descripcion: Descripción detallada (10-500 caracteres).
            
        Returns:
            str: Confirmación del registro.
        """
        try:
            input_data = IncidenciaInput(
                categoria=categoria,
                descripcion=descripcion
            )
            id_registro = db.registrar_incidencia(
                input_data.categoria,
                input_data.descripcion
            )
            return f"✅ Incidencia registrada (ID: {id_registro}) - Categoría: {categoria}"
            
        except Exception as e:
            return f"❌ Error: {str(e)}"

    def _buscar_receta_por_nombre(nombre_receta: str) -> str:
        """
        Busca una receta en la base de datos local por nombre o ID.
        
        SOLO busca en el RAG local (SQLite), NO usa el LLM para generar recetas.
        
        Args:
            nombre_receta: Nombre o ID de la receta a buscar.
            
        Returns:
            str: Receta encontrada con ingredientes e instrucciones, o error si no existe.
        """
        try:
            cursor = db._get_connection().__enter__()
            
            # Intentar buscar por ID primero
            cursor.execute(
                "SELECT * FROM recetas WHERE id_receta = ?", (nombre_receta,)
            )
            row = cursor.fetchone()
            
            # Si no encuentra por ID, buscar por nombre (LIKE)
            if not row:
                cursor.execute(
                    "SELECT * FROM recetas WHERE nombre LIKE ?", (f"%{nombre_receta}%",)
                )
                row = cursor.fetchone()
            
            if not row:
                return f"❌ No se encontró la receta '{nombre_receta}' en la base de datos local."
            
            receta = dict(row)
            ingredientes = json.loads(receta["ingredientes_json"])
            
            salida = [
                f"📖 {receta['nombre']}",
                f"🏷️ Categoría: {receta['categoria']}",
                f"⏱️ Tiempo: {receta['tiempo_prep']} min",
                f"💰 Costo: ${receta['costo']:.2f}",
                "",
                "🥗 Ingredientes:",
            ]
            
            for ing in ingredientes:
                salida.append(f"  - {ing['cantidad']} {ing['unidad']} de {ing['nombre']}")
            
            if receta.get("alergenos"):
                salida.append(f"\n⚠️ Alérgenos: {receta['alergenos']}")
            
            if receta.get("instrucciones"):
                salida.append(f"\n📝 Instrucciones:\n{receta['instrucciones']}")
            
            return "\n".join(salida)
            
        except Exception as e:
            return f"❌ Error en búsqueda: {str(e)}"

    def _analizar_rentabilidad_menu() -> str:
        """
        Analiza la rentabilidad del menú usando matriz BCG.
        
        Clasifica cada receta en:
        - 🌟 Estrellas: Alto margen (>40%), Alta venta (>10)
        - 🐮 Vacas: Alto margen, Baja venta
        - ❓ Interrogantes: Bajo margen, Alta venta
        - 🐶 Perros: Bajo margen, Baja venta
        
        Returns:
            str: Reporte completo de rentabilidad.
        """
        try:
            resultado = db.analizar_rentabilidad_menu()
            output = AnalisisRentabilidadOutput(**resultado)
            
            lineas = ["📊 ANÁLISIS DE RENTABILIDAD DEL MENÚ", "=" * 40, ""]
            
            if output.estrellas:
                lineas.append("🌟 ESTRELLAS (Alto margen, Alta venta):")
                for item in output.estrellas:
                    lineas.append(f"  - {item['nombre']}: {item['unidades_vendidas']} ventas, {item['margen_promedio']}% margen")
                lineas.append("")
            
            if output.vacas:
                lineas.append("🐮 VACAS (Alto margen, Baja venta):")
                for item in output.vacas:
                    lineas.append(f"  - {item['nombre']}: {item['unidades_vendidas']} ventas, {item['margen_promedio']}% margen")
                lineas.append("")
            
            if output.interrogantes:
                lineas.append("❓ INTERROGANTES (Bajo margen, Alta venta):")
                for item in output.interrogantes:
                    lineas.append(f"  - {item['nombre']}: {item['unidades_vendidas']} ventas, {item['margen_promedio']}% margen")
                lineas.append("")
            
            if output.perros:
                lineas.append("🐶 PERROS (Bajo margen, Baja venta):")
                for item in output.perros:
                    lineas.append(f"  - {item['nombre']}: {item['unidades_vendidas']} ventas, {item['margen_promedio']}% margen")
                lineas.append("")
            
            lineas.append("=" * 40)
            lineas.append(output.resumen)
            
            return "\n".join(lineas)
            
        except Exception as e:
            return f"❌ Error en análisis: {str(e)}"

    tools = [
        Tool(
            name="buscar_receta_por_nombre",
            func=_buscar_receta_por_nombre,
            description="""
                Busca una receta en la base de datos local (RAG) por nombre o ID.
                SOLO busca en SQLite, NO genera recetas nuevas.
                Entrada: nombre_receta (str) - Nombre o ID de la receta
                Ejemplo: buscar_receta_por_nombre("Pato") o buscar_receta_por_nombre("REC001")
            """,
        ),
        Tool(
            name="obtener_ingredientes_por_caducar",
            func=_obtener_ingredientes_por_caducar,
            description="""
                Consulta ingredientes que caducarán en los próximos N días.
                Usa política FEFO para identificar productos urgentes.
                Entrada: dias_limite (int, 1-90)
                Ejemplo: obtener_ingredientes_por_caducar(5)
            """,
        ),
        Tool(
            name="registrar_uso_inventario",
            func=_registrar_uso_inventario,
            description="""
                Registra el uso de un ingrediente del inventario.
                Descuenta del lote más antiguo (FEFO).
                Entrada: nombre_item (str), cantidad_usada (float)
                Ejemplo: registrar_uso_inventario("Fresa", 2.5)
            """,
        ),
        Tool(
            name="escalar_receta",
            func=_escalar_receta,
            description="""
                Escala matemáticamente una receta para N comensales.
                Multiplica ingredientes por factor de escala.
                Entrada: receta_id (int), comensales (int)
                Ejemplo: escalar_receta(1, 50)
            """,
        ),
        Tool(
            name="registrar_incidencia",
            func=_registrar_incidencia,
            description="""
                Registra una incidencia en bitácora diaria.
                Categorías: Operativa, Calidad, Inventario, Venta, etc.
                Entrada: categoria (str), descripcion (str)
                Ejemplo: registrar_incidencia("Inventario", "Falta leche")
            """,
        ),
        Tool(
            name="analizar_rentabilidad_menu",
            func=_analizar_rentabilidad_menu,
            description="""
                Analiza rentabilidad del menú con matriz BCG.
                Clasifica en: Estrellas, Vacas, Interrogantes, Perros.
                No requiere parámetros.
                Ejemplo: analizar_rentabilidad_menu()
            """,
        ),
    ]
    
    return tools