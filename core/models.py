from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class Ingrediente(BaseModel):
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
        import re
        if not re.match(r"\d{4}-\d{2}-\d{2}", v):
            raise ValueError("Fecha debe estar en formato YYYY-MM-DD")
        return v

    def to_dict(self) -> dict:
        return self.model_dump()


class AccionOffice(BaseModel):
    herramienta: str = Field(...)
    operacion: str = Field(...)
    ruta_archivo: str = Field(..., min_length=1)
    payload: dict = Field(default_factory=dict)
    requiere_hitl: bool = Field(default=True)

    @field_validator("herramienta")
    @classmethod
    def herramienta_valida(cls, v: str) -> str:
        if v.lower() not in {"word", "excel"}:
            raise ValueError("Herramienta debe ser 'word' o 'excel'")
        return v.lower()

    @field_validator("operacion")
    @classmethod
    def operacion_valida(cls, v: str) -> str:
        if v.lower() not in {"leer", "escribir", "crear"}:
            raise ValueError("Operacion debe ser 'leer', 'escribir' o 'crear'")
        return v.lower()

    def to_dict(self) -> dict:
        return self.model_dump()