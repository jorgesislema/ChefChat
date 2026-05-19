"""
Modelos de Datos para ChefChat Pro - Pydantic V2

Este módulo define todos los esquemas de datos validados que utiliza
el sistema para operaciones de inventario, recetas, ventas e incidencias.
"""

from typing import List
from datetime import datetime, date
from pydantic import BaseModel, Field, field_validator
import re


# =============================================================================
# MODELOS LEGACY (Compatibilidad con GUI y Worker)
# =============================================================================

class Ingrediente(BaseModel):
    """Modelo legacy para ingredientes (compatibilidad)."""
    nombre: str = Field(..., min_length=1, max_length=100)
    cantidad: float = Field(..., gt=0)
    unidad: str = Field(..., min_length=1, max_length=20)

    @field_validator("nombre")
    @classmethod
    def nombre_minuscula(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("unidad")
    @classmethod
    def unidad_valida(cls, v: str) -> str:
        unidades_validas = {"g", "kg", "ml", "L", "unidad", "cups", "tbsp", "tsp"}
        if v.lower() not in unidades_validas:
            raise ValueError(f"Unidad '{v}' no valida")
        return v.lower()

    def to_dict(self) -> dict:
        return self.model_dump()


class Receta(BaseModel):
    """Modelo legacy para recetas (compatibilidad)."""
    id_receta: str = Field(..., min_length=1)
    nombre: str = Field(..., min_length=1, max_length=200)
    ingredientes: List[Ingrediente] = Field(..., min_length=1)
    alergenos: List[str] = Field(default_factory=list)
    costo_estimado: float = Field(..., ge=0)

    @field_validator("alergenos")
    @classmethod
    def alergenos_no_vacios(cls, v: List[str]) -> List[str]:
        return [a.strip() for a in v if a.strip()]

    def to_dict(self) -> dict:
        return self.model_dump()


class Evento(BaseModel):
    """Modelo legacy para eventos (compatibilidad)."""
    id_evento: str = Field(..., min_length=1)
    tipo_evento: str = Field(..., min_length=1)
    fecha: str = Field(...)
    presupuesto: float = Field(..., ge=0)
    estado_aprobacion: str = Field(default="pendiente")

    @field_validator("estado_aprobacion")
    @classmethod
    def estado_valido(cls, v: str) -> str:
        estados_validos = {"pendiente", "aprobado", "rechazado"}
        if v.lower() not in estados_validos:
            raise ValueError(f"Estado '{v}' no valido")
        return v.lower()

    @field_validator("fecha")
    @classmethod
    def fecha_valida(cls, v: str) -> str:
        if not re.match(r"\d{4}-\d{2}-\d{2}", v):
            raise ValueError("Fecha debe estar en formato YYYY-MM-DD")
        return v

    def to_dict(self) -> dict:
        return self.model_dump()


class AccionOffice(BaseModel):
    """Modelo para acciones de Office con soporte COM (Word, Excel, PowerPoint)."""
    herramienta: str = Field(...)
    operacion: str = Field(...)
    ruta_archivo: str = Field(default="", min_length=0)
    payload: dict = Field(default_factory=dict)
    requiere_hitl: bool = Field(default=True)

    @field_validator("herramienta")
    @classmethod
    def herramienta_valida(cls, v: str) -> str:
        if v.lower() not in {"word", "excel", "powerpoint", "power point"}:
            raise ValueError("Herramienta debe ser 'word', 'excel' o 'powerpoint'")
        return "powerpoint" if v.lower() == "power point" else v.lower()

    @field_validator("operacion")
    @classmethod
    def operacion_valida(cls, v: str) -> str:
        if v.lower() not in {"leer", "escribir", "crear", "enviar", "plantilla"}:
            raise ValueError("Operacion debe ser 'leer', 'escribir', 'crear', 'enviar' o 'plantilla'")
        return v.lower()

    def to_dict(self) -> dict:
        return self.model_dump()


# =============================================================================
# MODELOS NUEVOS (ChefChat Pro v2.0)
# =============================================================================


class Catalogo(BaseModel):
    """
    Modelo para el catálogo de productos del restaurante.
    
    Attributes:
        id: Identificador único del producto.
        nombre: Nombre del producto (ej. 'Fresa', 'Pollo').
        categoria: Categoría del producto (Fresco, Congelado, Seco, etc.).
        vida_util_dias: Días de vida útil desde la fecha de ingreso.
    """
    id: int = Field(..., gt=0)
    nombre: str = Field(..., min_length=1, max_length=100)
    categoria: str = Field(..., min_length=1, max_length=50)
    vida_util_dias: int = Field(..., gt=0, le=365)

    @field_validator("nombre", "categoria")
    @classmethod
    def validar_texto(cls, v: str) -> str:
        """Valida que el texto no tenga caracteres especiales inválidos."""
        if not re.match(r"^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s\-]+$", v):
            raise ValueError(f"El campo contiene caracteres inválidos: {v}")
        return v.strip().title()


class Inventario(BaseModel):
    """
    Modelo para el registro de inventario.
    
    Attributes:
        id: Identificador único del registro.
        producto_id: Referencia al producto en Catálogo.
        fecha_ingreso: Fecha de ingreso del producto al almacén.
        cantidad: Cantidad disponible del producto.
        unidad: Unidad de medida (kg, g, L, unidad, etc.).
    """
    id: int = Field(..., gt=0)
    producto_id: int = Field(..., gt=0)
    fecha_ingreso: date = Field(...)
    cantidad: float = Field(..., gt=0)
    unidad: str = Field(..., min_length=1, max_length=20)

    @field_validator("unidad")
    @classmethod
    def validar_unidad(cls, v: str) -> str:
        """Valida que la unidad sea una de las permitidas."""
        unidades_validas = {"kg", "g", "l", "ml", "unidad", "pieza", "paquete", "caja"}
        v_lower = v.lower().strip()
        if v_lower not in unidades_validas:
            raise ValueError(f"Unidad '{v}' no válida. Use: {unidades_validas}")
        return v_lower

    def calcular_fecha_caducidad(self, vida_util_dias: int) -> date:
        """Calcula la fecha de caducidad basada en la vida útil del producto."""
        from datetime import timedelta
        return self.fecha_ingreso + timedelta(days=vida_util_dias)


class VistaCaducidad(BaseModel):
    """
    Modelo para la vista SQL de caducidad.
    
    Esta vista une Inventario con Catálogo para calcular la fecha
    de caducidad efectiva de cada lote en almacén.
    
    Attributes:
        inventario_id: ID del registro de inventario.
        producto_nombre: Nombre del producto.
        categoria: Categoría del producto.
        fecha_ingreso: Fecha de ingreso.
        cantidad: Cantidad disponible.
        unidad: Unidad de medida.
        vida_util_dias: Vida útil del producto.
        fecha_caducidad_efectiva: Fecha calculada de caducidad.
        dias_restantes: Días restantes para caducar (puede ser negativo).
    """
    inventario_id: int = Field(..., gt=0)
    producto_nombre: str = Field(..., min_length=1)
    categoria: str = Field(..., min_length=1)
    fecha_ingreso: date = Field(...)
    cantidad: float = Field(..., gt=0)
    unidad: str = Field(...)
    vida_util_dias: int = Field(..., gt=0)
    fecha_caducidad_efectiva: date = Field(...)
    dias_restantes: int = Field(...)


class BitacoraDiaria(BaseModel):
    """
    Modelo para la bitácora diaria de incidencias y eventos.
    
    Attributes:
        id: Identificador único del registro.
        timestamp: Fecha y hora del evento.
        categoria: Categoría de la incidencia (Operativa, Calidad, etc.).
        descripcion: Descripción detallada del evento.
    """
    id: int = Field(..., gt=0)
    timestamp: datetime = Field(default_factory=datetime.now)
    categoria: str = Field(..., min_length=1, max_length=50)
    descripcion: str = Field(..., min_length=1, max_length=500)

    @field_validator("categoria")
    @classmethod
    def validar_categoria(cls, v: str) -> str:
        """Valida que la categoría sea una de las permitidas."""
        categorias_validas = {
            "Operativa", "Calidad", "Inventario", "Venta",
            "Mantenimiento", "Personal", "Proveedor", "Otro"
        }
        v_title = v.strip().title()
        if v_title not in categorias_validas:
            raise ValueError(f"Categoría '{v}' no válida. Use: {categorias_validas}")
        return v_title


class VentasHistoricas(BaseModel):
    """
    Modelo para el histórico de ventas.
    
    Attributes:
        id: Identificador único del registro.
        receta_id: Referencia a la receta vendida.
        receta_nombre: Nombre de la receta (para reporting).
        unidades_vendidas: Cantidad de unidades vendidas.
        precio_venta: Precio de venta unitario.
        costo_produccion: Costo de producción unitario.
        fecha_venta: Fecha de la venta.
    """
    id: int = Field(..., gt=0)
    receta_id: int = Field(..., gt=0)
    receta_nombre: str = Field(..., min_length=1, max_length=200)
    unidades_vendidas: int = Field(..., gt=0)
    precio_venta: float = Field(..., gt=0)
    costo_produccion: float = Field(..., ge=0)
    fecha_venta: date = Field(default_factory=date.today)

    @property
    def margen_unitario(self) -> float:
        """Calcula el margen de ganancia unitario."""
        return self.precio_venta - self.costo_produccion

    @property
    def margen_porcentaje(self) -> float:
        """Calcula el margen de ganancia en porcentaje."""
        if self.precio_venta == 0:
            return 0.0
        return (self.margen_unitario / self.precio_venta) * 100

    @property
    def ganancia_total(self) -> float:
        """Calcula la ganancia total de la venta."""
        return self.margen_unitario * self.unidades_vendidas


class IncidenciaInput(BaseModel):
    """
    Modelo de entrada para registrar incidencias.
    
    Attributes:
        categoria: Categoría de la incidencia.
        descripcion: Descripción detallada.
    """
    categoria: str = Field(..., min_length=1, max_length=50)
    descripcion: str = Field(..., min_length=10, max_length=500)


class UsoInventarioInput(BaseModel):
    """
    Modelo de entrada para registrar uso de inventario.
    
    Attributes:
        nombre_item: Nombre del producto a usar.
        cantidad_usada: Cantidad a descontar.
    """
    nombre_item: str = Field(..., min_length=1, max_length=100)
    cantidad_usada: float = Field(..., gt=0)


class EscalarRecetaInput(BaseModel):
    """
    Modelo de entrada para escalar recetas.
    
    Attributes:
        receta_id: ID de la receta a escalar.
        comensales: Número de comensales deseado.
    """
    receta_id: int = Field(..., gt=0)
    comensales: int = Field(..., gt=0)


class CaducidadInput(BaseModel):
    """
    Modelo de entrada para consulta de caducidad.
    
    Attributes:
        dias_limite: Número de días límite para la consulta.
    """
    dias_limite: int = Field(..., gt=0, le=90)


class AnalisisRentabilidadOutput(BaseModel):
    """
    Modelo de salida para análisis de rentabilidad.
    
    Attributes:
        estrellas: Recetas de alto margen y alta venta.
        vacas: Recetas de alto margen y baja venta.
        interrogantes: Recetas de bajo margen y alta venta.
        perros: Recetas de bajo margen y baja venta.
    """
    estrellas: List[dict] = Field(default_factory=list)
    vacas: List[dict] = Field(default_factory=list)
    interrogantes: List[dict] = Field(default_factory=list)
    perros: List[dict] = Field(default_factory=list)
    resumen: str = Field(default="")