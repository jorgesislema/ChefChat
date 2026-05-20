"""Pydantic contracts for strict tool input/output validation."""
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime, date
import json


# ── Tool Input Contracts ──

class ToolInputBase(BaseModel):
    """Base model for all tool inputs."""
    class Config:
        extra = "forbid"  # Reject unknown fields


class SobrantesInput(ToolInputBase):
    """Input for sobrantes operations."""
    producto: str = Field(..., min_length=1, max_length=100, description="Nombre del producto")
    cantidad: float = Field(..., gt=0, description="Cantidad sobrante")
    unidad: str = Field(..., min_length=1, max_length=20, description="Unidad de medida")
    turno: Optional[str] = Field(default=None, max_length=50, description="Turno de produccion")
    destino: str = Field(default="reutilizado", description="Destino del sobrante")
    dias_reutilizacion: Optional[int] = Field(default=None, gt=0, le=30, description="Dias para reutilizacion sanitaria")
    id_empleado: Optional[int] = Field(default=None, gt=0, description="ID del empleado")
    
    @field_validator("unidad")
    @classmethod
    def validar_unidad(cls, v: str) -> str:
        unidades_validas = {"kg", "g", "l", "ml", "unidad", "pieza", "paquete", "caja", "porcion"}
        v_lower = v.lower().strip()
        if v_lower not in unidades_validas:
            raise ValueError(f"Unidad '{v}' no valida. Use: {unidades_validas}")
        return v_lower
    
    @field_validator("destino")
    @classmethod
    def validar_destino(cls, v: str) -> str:
        destinos_validos = {"reutilizado", "desperdicio", "donacion", "compostaje"}
        v_lower = v.lower().strip()
        if v_lower not in destinos_validos:
            raise ValueError(f"Destino '{v}' no valido. Use: {destinos_validos}")
        return v_lower


class MermaInput(ToolInputBase):
    """Input for merma operations."""
    producto: str = Field(..., min_length=1, max_length=100, description="Nombre del producto")
    cantidad: float = Field(..., gt=0, description="Cantidad de merma")
    unidad: str = Field(..., min_length=1, max_length=20, description="Unidad de medida")
    motivo: str = Field(..., min_length=1, max_length=200, description="Motivo de la merma")
    costo_estimado: Optional[float] = Field(default=0, ge=0, description="Costo estimado de la merma")
    
    @field_validator("unidad")
    @classmethod
    def validar_unidad(cls, v: str) -> str:
        unidades_validas = {"kg", "g", "l", "ml", "unidad", "pieza", "paquete", "caja", "porcion"}
        v_lower = v.lower().strip()
        if v_lower not in unidades_validas:
            raise ValueError(f"Unidad '{v}' no valida. Use: {unidades_validas}")
        return v_lower


class TrabajadorInput(ToolInputBase):
    """Input for trabajador operations."""
    nombre_completo: str = Field(..., min_length=1, max_length=150, description="Nombre completo del trabajador")
    cargo: Optional[str] = Field(default=None, max_length=100, description="Cargo del trabajador")
    turno: Optional[str] = Field(default=None, max_length=50, description="Turno de trabajo")
    hora_entrada: Optional[str] = Field(default=None, max_length=5, description="Hora de entrada (HH:MM)")
    hora_salida: Optional[str] = Field(default=None, max_length=5, description="Hora de salida (HH:MM)")
    dias_descanso: Optional[str] = Field(default=None, max_length=50, description="Dias de descanso")
    telefono: Optional[str] = Field(default=None, max_length=20, description="Numero de telefono")
    estado: str = Field(default="activo", description="Estado del trabajador")
    tipo_contrato: str = Field(default="fijo", description="Tipo de contrato")
    
    @field_validator("estado")
    @classmethod
    def validar_estado(cls, v: str) -> str:
        estados_validos = {"activo", "reposo", "vacaciones", "baja"}
        v_lower = v.lower().strip()
        if v_lower not in estados_validos:
            raise ValueError(f"Estado '{v}' no valido. Use: {estados_validos}")
        return v_lower
    
    @field_validator("tipo_contrato")
    @classmethod
    def validar_tipo_contrato(cls, v: str) -> str:
        tipos_validos = {"fijo", "temporal", "practicas", "eventual"}
        v_lower = v.lower().strip()
        if v_lower not in tipos_validos:
            raise ValueError(f"Tipo de contrato '{v}' no valido. Use: {tipos_validos}")
        return v_lower


class InventarioInput(ToolInputBase):
    """Input for inventario operations."""
    producto_id: int = Field(..., gt=0, description="ID del producto en catalogo")
    cantidad: float = Field(..., gt=0, description="Cantidad del producto")
    unidad: str = Field(..., min_length=1, max_length=20, description="Unidad de medida")
    fecha_ingreso: Optional[str] = Field(default=None, description="Fecha de ingreso (YYYY-MM-DD)")
    id_lote: Optional[str] = Field(default=None, max_length=50, description="ID del lote")
    fecha_caducidad: Optional[str] = Field(default=None, description="Fecha de caducidad (YYYY-MM-DD)")
    
    @field_validator("unidad")
    @classmethod
    def validar_unidad(cls, v: str) -> str:
        unidades_validas = {"kg", "g", "l", "ml", "unidad", "pieza", "paquete", "caja"}
        v_lower = v.lower().strip()
        if v_lower not in unidades_validas:
            raise ValueError(f"Unidad '{v}' no valida. Use: {unidades_validas}")
        return v_lower
    
    @field_validator("fecha_ingreso", "fecha_caducidad")
    @classmethod
    def validar_fecha(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        try:
            date.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError(f"Fecha '{v}' no valida. Use formato YYYY-MM-DD")


class VentaInput(ToolInputBase):
    """Input for venta operations."""
    receta_id: int = Field(..., gt=0, description="ID de la receta vendida")
    receta_nombre: str = Field(..., min_length=1, max_length=200, description="Nombre de la receta")
    unidades_vendidas: int = Field(..., gt=0, description="Cantidad de unidades vendidas")
    precio_venta: float = Field(..., gt=0, description="Precio de venta unitario")
    costo_produccion: float = Field(..., ge=0, description="Costo de produccion unitario")
    fecha_venta: Optional[str] = Field(default=None, description="Fecha de venta (YYYY-MM-DD)")


class DashboardInput(ToolInputBase):
    """Input for dashboard operations."""
    dias: int = Field(default=7, gt=0, le=365, description="Numero de dias para el dashboard")
    tipo: str = Field(default="sobrantes", description="Tipo de dashboard")
    
    @field_validator("tipo")
    @classmethod
    def validar_tipo(cls, v: str) -> str:
        tipos_validos = {"sobrantes", "mermas", "personal", "ventas", "produccion"}
        v_lower = v.lower().strip()
        if v_lower not in tipos_validos:
            raise ValueError(f"Tipo '{v}' no valido. Use: {tipos_validos}")
        return v_lower


class MenuInput(ToolInputBase):
    """Input for menu operations."""
    dia: str = Field(..., min_length=1, max_length=20, description="Dia de la semana")
    comida: str = Field(..., min_length=1, max_length=50, description="Tipo de comida")
    receta_id: Optional[int] = Field(default=None, gt=0, description="ID de la receta")
    precio: Optional[float] = Field(default=None, gt=0, description="Precio del plato")


# ── Tool Output Contracts ──

class ToolOutputBase(BaseModel):
    """Base model for all tool outputs."""
    exito: bool = Field(..., description="Indica si la operacion fue exitosa")
    mensaje: str = Field(default="", description="Mensaje descriptivo")
    datos: Optional[Dict[str, Any]] = Field(default=None, description="Datos de resultado")


class SobrantesOutput(ToolOutputBase):
    """Output for sobrantes operations."""
    id_sobrante: Optional[int] = Field(default=None, description="ID del sobrante registrado")
    total_sobrantes: Optional[int] = Field(default=None, description="Total de sobrantes en el periodo")
    cantidad_total: Optional[float] = Field(default=None, description="Cantidad total de sobrantes")


class MermaOutput(ToolOutputBase):
    """Output for merma operations."""
    id_merma: Optional[int] = Field(default=None, description="ID de la merma registrada")
    total_mermas: Optional[int] = Field(default=None, description="Total de mermas en el periodo")
    costo_total: Optional[float] = Field(default=None, description="Costo total de mermas")


class TrabajadorOutput(ToolOutputBase):
    """Output for trabajador operations."""
    id_trabajador: Optional[int] = Field(default=None, description="ID del trabajador")
    trabajadores: Optional[List[Dict[str, Any]]] = Field(default=None, description="Lista de trabajadores")


class InventarioOutput(ToolOutputBase):
    """Output for inventario operations."""
    id_inventario: Optional[int] = Field(default=None, description="ID del registro de inventario")
    stock_actual: Optional[float] = Field(default=None, description="Stock actual del producto")
    productos_proximos_caducar: Optional[List[Dict[str, Any]]] = Field(default=None, description="Productos proximos a caducar")


class VentaOutput(ToolOutputBase):
    """Output for venta operations."""
    id_venta: Optional[int] = Field(default=None, description="ID de la venta registrada")
    ganancia_total: Optional[float] = Field(default=None, description="Ganancia total de la venta")
    margen_porcentaje: Optional[float] = Field(default=None, description="Margen de ganancia en porcentaje")


class DashboardOutput(ToolOutputBase):
    """Output for dashboard operations."""
    filepath: Optional[str] = Field(default=None, description="Ruta del archivo exportado")
    kpis: Optional[Dict[str, Any]] = Field(default=None, description="KPIs del dashboard")
    charts: Optional[List[str]] = Field(default=None, description="Lista de graficos generados")


class MenuOutput(ToolOutputBase):
    """Output for menu operations."""
    id_menu: Optional[int] = Field(default=None, description="ID del menu")
    menu_semanal: Optional[Dict[str, Any]] = Field(default=None, description="Menu semanal completo")


# ── HITL Output Contract ──

class HITLOutput(ToolOutputBase):
    """Output for HITL (Human-in-the-Loop) operations."""
    requiere_aprobacion: bool = Field(default=True, description="Indica si requiere aprobacion humana")
    accion: Optional[Dict[str, Any]] = Field(default=None, description="Accion pendiente de aprobacion")
    preview: Optional[str] = Field(default=None, description="Preview de la accion")


# ── Validation Helpers ──

def validate_tool_input(tool_name: str, data: Dict[str, Any]) -> ToolInputBase:
    """Validate tool input against the appropriate contract."""
    contracts = {
        "registrar_sobrante": SobrantesInput,
        "registrar_merma": MermaInput,
        "registrar_trabajador": TrabajadorInput,
        "registrar_inventario": InventarioInput,
        "registrar_venta": VentaInput,
        "dashboard": DashboardInput,
        "menu": MenuInput,
    }
    
    contract = contracts.get(tool_name)
    if contract is None:
        raise ValueError(f"No contract defined for tool: {tool_name}")
    
    return contract(**data)


def validate_tool_output(tool_name: str, data: Dict[str, Any]) -> ToolOutputBase:
    """Validate tool output against the appropriate contract."""
    contracts = {
        "registrar_sobrante": SobrantesOutput,
        "registrar_merma": MermaOutput,
        "registrar_trabajador": TrabajadorOutput,
        "registrar_inventario": InventarioOutput,
        "registrar_venta": VentaOutput,
        "dashboard": DashboardOutput,
        "menu": MenuOutput,
        "hitl": HITLOutput,
    }
    
    contract = contracts.get(tool_name, ToolOutputBase)
    return contract(**data)
