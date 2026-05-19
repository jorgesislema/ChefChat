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
    Modelo para el catalogo de productos del restaurante.
    
    Attributes:
        id: Identificador unico del producto (0 para nuevos).
        nombre: Nombre del producto (ej. 'Fresa', 'Pollo').
        categoria: Categoria del producto (Fresco, Congelado, Seco, etc.).
        vida_util_dias: Dias de vida util desde la fecha de ingreso.
    """
    id: int = Field(default=0, ge=0)
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
    id: int = Field(default=0, ge=0)
    producto_id: int = Field(default=0, ge=0)
    fecha_ingreso: date = Field(...)
    cantidad: float = Field(..., gt=0)
    unidad: str = Field(..., min_length=1, max_length=20)

    @field_validator("unidad")
    @classmethod
    def validar_unidad(cls, v: str) -> str:
        """Valida que la unidad sea una de las permitidas."""
        unidades_validas = {
            "kg", "g", "l", "ml", "unidad", "und", "pieza", "pza",
            "paquete", "pqt", "caja", "bolsa", "qq", "quintal", "kintal",
            "porcion", "botella", "gal", "galon", "lb", "libra", "oz", "onza",
            "lote", "cubeta", "saco", "bidon", "rollo", "pliego", "tarro",
            "frasco", "sobre", "barra", "display", "bulto", "charola"
        }
        v_lower = v.lower().strip()
        if v_lower not in unidades_validas:
            raise ValueError(f"Unidad '{v}' no valida. Use: {sorted(unidades_validas)}")
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


# =============================================================================
# MODELOS v2.0 - Personal, Mermas, Compras, Menu, Documentos
# =============================================================================


class Trabajador(BaseModel):
    """Personal del restaurante."""
    id_empleado: str = Field(..., min_length=3, max_length=20)
    nombre_completo: str = Field(..., min_length=1, max_length=100)
    cargo: str = Field(..., min_length=1, max_length=50)
    turno: str = Field(..., min_length=3, max_length=20)
    hora_entrada: str = Field(default="", max_length=10)
    hora_salida: str = Field(default="", max_length=10)
    dias_descanso: str = Field(default="")
    tipo_contrato: str = Field(default="fijo")
    estado: str = Field(default="activo")
    fecha_inicio_contrato: date | None = Field(default=None)
    fecha_fin_contrato: date | None = Field(default=None)
    fecha_inicio_ausencia: date | None = Field(default=None)
    fecha_fin_ausencia: date | None = Field(default=None)
    motivo_ausencia: str = Field(default="")

    @field_validator("tipo_contrato")
    @classmethod
    def validar_contrato(cls, v: str) -> str:
        tipos = {"fijo", "temporal", "practicante", "honorarios"}
        if v.lower() not in tipos:
            raise ValueError(f"Tipo contrato '{v}' no valido. Use: {tipos}")
        return v.lower()

    @field_validator("estado")
    @classmethod
    def validar_estado(cls, v: str) -> str:
        estados = {"activo", "reposo_medico", "permiso_maternidad",
                   "permiso_personal", "vacaciones", "suspendido", "baja"}
        if v.lower() not in estados:
            raise ValueError(f"Estado '{v}' no valido. Use: {estados}")
        return v.lower()

    @field_validator("turno")
    @classmethod
    def validar_turno(cls, v: str) -> str:
        turnos = {"matutino", "vespertino", "nocturno", "mixto"}
        if v.lower() not in turnos:
            raise ValueError(f"Turno '{v}' no valido. Use: {turnos}")
        return v.lower()

    @property
    def en_ausencia(self) -> bool:
        return self.estado != "activo"

    @property
    def dias_para_retorno(self) -> int | None:
        if self.fecha_fin_ausencia:
            return (self.fecha_fin_ausencia - date.today()).days
        return None


class AusenciaInput(BaseModel):
    """Registro de ausencia de personal."""
    id_empleado: str = Field(..., min_length=3, max_length=20)
    tipo: str = Field(...)
    fecha_inicio: str = Field(..., min_length=10, max_length=10)
    fecha_fin: str = Field(..., min_length=10, max_length=10)
    motivo: str = Field(default="")

    @field_validator("tipo")
    @classmethod
    def validar_tipo_ausencia(cls, v: str) -> str:
        tipos = {"reposo_medico", "permiso_maternidad", "vacaciones",
                 "permiso_personal", "permiso_paternidad", "suspendido"}
        v_norm = v.lower().replace(" ", "_")
        if v_norm not in tipos:
            raise ValueError(f"Tipo ausencia '{v}' no valido. Use: {tipos}")
        return v_norm

    @field_validator("fecha_inicio", "fecha_fin")
    @classmethod
    def validar_fecha_iso(cls, v: str) -> str:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            raise ValueError("Fecha debe estar en formato YYYY-MM-DD")
        return v


class ReincorporarInput(BaseModel):
    """Reincorporacion de trabajador tras ausencia."""
    id_empleado: str = Field(..., min_length=3, max_length=20)


class PermisoRapidoInput(BaseModel):
    """Registro de permiso en lenguaje natural."""
    mensaje: str = Field(..., min_length=10, max_length=500)


class MermaInput(BaseModel):
    """Registro de merma/desperdicio."""
    producto: str = Field(..., min_length=1, max_length=100)
    cantidad: float = Field(..., gt=0)
    unidad: str = Field(..., min_length=1, max_length=20)
    motivo: str = Field(..., min_length=1, max_length=200)
    costo_estimado: float = Field(default=0.0, ge=0)

    @field_validator("producto")
    @classmethod
    def limpiar_producto(cls, v: str) -> str:
        return v.strip().title()


class MermaReporteOutput(BaseModel):
    """Reporte de mermas en un periodo."""
    periodo_dias: int = Field(default=7, gt=0, le=365)
    total_registros: int = Field(default=0, ge=0)
    cantidad_total: float = Field(default=0.0, ge=0)
    costo_total: float = Field(default=0.0, ge=0)
    por_tipo: dict = Field(default_factory=dict)
    por_dia: dict = Field(default_factory=dict)
    top_productos: list = Field(default_factory=list)
    resumen: str = Field(default="")


class CompraInput(BaseModel):
    """Registro de compra en lenguaje natural o estructurado."""
    mensaje: str = Field(..., min_length=5, max_length=500)
    # Campos extraidos automaticamente:
    producto: str = Field(default="")
    cantidad: float = Field(default=0.0, gt=0)
    unidad: str = Field(default="")
    fecha_caducidad: str = Field(default="")
    categoria: str = Field(default="General")

    @field_validator("producto")
    @classmethod
    def limpiar_producto(cls, v: str) -> str:
        return v.strip().title() if v else v


class BajaInventarioInput(BaseModel):
    """Dar de baja producto del inventario (rotura/dano)."""
    producto: str = Field(..., min_length=1, max_length=100)
    cantidad: float = Field(..., gt=0)
    unidad: str = Field(..., min_length=1, max_length=20)
    motivo: str = Field(..., min_length=1, max_length=200)
    costo: float = Field(default=0.0, ge=0)


class MenuPlato(BaseModel):
    """Plato individual del menu semanal."""
    id_plan: str = Field(default="")
    dia_semana: str = Field(..., min_length=3, max_length=15)
    tipo_servicio: str = Field(..., min_length=3, max_length=20)
    nombre_plato: str = Field(..., min_length=1, max_length=200)
    precio_venta: float = Field(default=0.0, ge=0)
    requiere_prep_previa: bool = Field(default=False)

    @field_validator("dia_semana")
    @classmethod
    def validar_dia(cls, v: str) -> str:
        dias = {"lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"}
        if v.lower() not in dias:
            raise ValueError(f"Dia '{v}' no valido. Use: {dias}")
        return v.title()

    @field_validator("tipo_servicio")
    @classmethod
    def validar_servicio(cls, v: str) -> str:
        servicios = {"desayuno", "almuerzo", "merienda", "cena", "a_la_carta", "especial"}
        v_norm = v.lower().replace(" ", "_")
        if v_norm not in servicios:
            raise ValueError(f"Servicio '{v}' no valido. Use: {servicios}")
        return v_norm


class MenuSemanalOutput(BaseModel):
    """Menu semanal completo."""
    semana: str = Field(default="")
    total_platos: int = Field(default=0, ge=0)
    platos: List[MenuPlato] = Field(default_factory=list)
    costo_promedio: float = Field(default=0.0, ge=0)
    resumen: str = Field(default="")


class DocumentoRAGModel(BaseModel):
    """Documento almacenado en el sistema RAG."""
    id: int = Field(default=0, ge=0)
    tipo: str = Field(...)
    nombre: str = Field(..., min_length=1, max_length=255)
    path: str = Field(default="")
    extension: str = Field(default="")
    tamano_bytes: int = Field(default=0, ge=0)
    contenido_preview: str = Field(default="")
    contenido_completo: str = Field(default="")
    palabras_clave: str = Field(default="")
    fecha_ingreso: datetime | None = Field(default=None)
    estado: str = Field(default="activo")

    @field_validator("tipo")
    @classmethod
    def validar_tipo_doc(cls, v: str) -> str:
        tipos = {"receta", "catalogo_inventario", "lotes_inventario",
                 "manual_bpm", "generico", "capacitacion", "personal"}
        if v.lower() not in tipos:
            raise ValueError(f"Tipo documento '{v}' no valido. Use: {tipos}")
        return v.lower()


class AlertasOutput(BaseModel):
    """Alertas cruzadas generadas por el sistema."""
    personal_ausente: List[dict] = Field(default_factory=list)
    productos_por_caducar: List[dict] = Field(default_factory=list)
    stock_bajo: List[dict] = Field(default_factory=list)
    sugerencias: List[str] = Field(default_factory=list)
    resumen: str = Field(default="")