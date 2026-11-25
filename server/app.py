"""Servidor local de ChefChat (FastAPI). Solo escucha en 127.0.0.1.

Arranque:  python -m server        (abre http://127.0.0.1:8765)
Sirve la pantalla web desde web/dist si ya esta construida.
"""

from __future__ import annotations

import os
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutTimeout
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import core.config  # noqa: F401  (carga .env)
from agents import vencimientos
from data.esquema import asegurar_esquema
from data import analisis as ana, balance as bal, carga, compras as com, conteos as cnt, inventario as inv, menu as men, proveedores as prov, recetas as rec, turnos as tur
from data.proveedores import DatoInvalido
from examenes import servicio as ex

RAIZ = Path(__file__).resolve().parent.parent
DB = os.environ.get("CHEFCHAT_DB_FILE") or str(RAIZ / "chefchat.db")  # CHEFCHAT_DB_FILE: probar o hacer demos sobre una copia
if os.environ.get("HMS_API_KEY"):
    os.environ.setdefault("CHEFCHAT_AI_PROVIDER", "custom")

asegurar_esquema(DB)
app = FastAPI(title="ChefChat", version="2.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
                   allow_methods=["*"], allow_headers=["*"])

_orq = None
_orq_lock = threading.Lock()
_pool = ThreadPoolExecutor(max_workers=2)
SEGUNDOS_CHAT = 60


def _orquestador():
    global _orq
    with _orq_lock:
        if _orq is None:
            from agents.orchestrator import Orchestrator
            from data.db_manager import DatabaseManager
            _orq = Orchestrator(db_manager=DatabaseManager(DB))
        return _orq


def _q(sql: str, args=()) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(sql, args)]
    finally:
        conn.close()


def _error(e: Exception):
    if isinstance(e, ex.ExamenError):
        raise HTTPException(400, str(e))
    raise e


# ------------------------------------------------------------------ general
@app.get("/api/salud")
def salud():
    return {"ok": True}


@app.get("/api/resumen")
def resumen():
    hoy = date.today()
    sem = vencimientos.vencen_en_semanas(1, hoy, DB)
    dic = vencimientos.vencen_en_mes(hoy.year, 12, DB)
    venc = vencimientos.ya_vencidos(hoy, DB)
    mermas = _q("SELECT motivo, round(sum(costo_estimado),2) AS costo, count(*) AS veces FROM Mermas "
                "GROUP BY motivo ORDER BY costo DESC LIMIT 5")
    personal = _q("SELECT estado, count(*) AS n FROM Trabajadores GROUP BY estado")
    return {
        "fecha": hoy.isoformat(),
        "vencen_7_dias": {"lotes": len(sem), "items": sem[:6]},
        "vencen_diciembre": {"lotes": len(dic)},
        "ya_vencidos": {"lotes": len(venc)},
        "mermas_por_motivo": mermas,
        "mermas_total": round(sum(m["costo"] or 0 for m in mermas), 2),
        "personal": personal,
        "examenes": ex.reporte(DB),
    }


@app.get("/api/vencimientos")
def api_vencimientos(semanas: int = 4, mes: Optional[int] = None):
    hoy = date.today()
    filas = vencimientos.vencen_en_mes(hoy.year, mes, DB) if mes else vencimientos.vencen_en_semanas(semanas, hoy, DB)
    return {"lotes": filas}


@app.get("/api/inventario")
def inventario():
    return {"productos": _q(
        "SELECT c.nombre AS producto, c.categoria, c.tipo, round(sum(i.cantidad_actual),1) AS stock, min(i.unidad) AS unidad "
        "FROM Inventario i JOIN Catalogo c ON c.id=i.producto_id WHERE i.cantidad_actual>0 "
        "GROUP BY c.id ORDER BY c.categoria, c.nombre")}


@app.get("/api/mermas")
def mermas():
    return {"mermas": _q("SELECT fecha, producto, cantidad, unidad, motivo, costo_estimado FROM Mermas "
                         "ORDER BY fecha DESC LIMIT 100")}


@app.get("/api/trabajadores")
def trabajadores():
    return {"trabajadores": _q("SELECT id_empleado, nombre_completo, cargo, turno FROM Trabajadores ORDER BY nombre_completo")}


# ------------------------------------------------------------------ chat
class ChatIn(BaseModel):
    mensaje: str = Field(min_length=1, max_length=2000)


@app.post("/api/chat")
def chat(datos: ChatIn):
    def _responder() -> str:
        return _orquestador().generar_respuesta([{"rol": "user", "contenido": datos.mensaje}])
    try:
        return {"respuesta": _pool.submit(_responder).result(timeout=SEGUNDOS_CHAT)}
    except FutTimeout:
        return {"respuesta": "Tardé demasiado en responder. Intenta de nuevo en un momento.", "error": True}
    except Exception as e:  # el chat nunca debe tumbar el servidor
        return {"respuesta": f"No pude responder ahora ({type(e).__name__}).", "error": True}


# ------------------------------------------------------------------ examenes
class IniciarIn(BaseModel):
    id_empleado: str
    tema: str
    modo: str
    n: int = Field(default=ex.N_DEFECTO, ge=1, le=30)


class RespIn(BaseModel):
    pregunta_id: int
    elegida: int = Field(ge=0, le=3)


class EstadoIn(BaseModel):
    estado: str
    editado: Optional[Dict[str, Any]] = None


@app.get("/api/examenes/temas")
def examen_temas():
    return {"temas": ex.temas(DB)}


@app.post("/api/examenes/iniciar")
def examen_iniciar(d: IniciarIn):
    try:
        return ex.iniciar_intento(d.id_empleado, d.tema, d.modo, d.n, DB)
    except Exception as e:
        _error(e)


@app.post("/api/examenes/{intento_id}/responder")
def examen_responder(intento_id: int, d: RespIn):
    try:
        return ex.responder(intento_id, d.pregunta_id, d.elegida, DB)
    except Exception as e:
        _error(e)


@app.post("/api/examenes/{intento_id}/cerrar")
def examen_cerrar(intento_id: int):
    try:
        return ex.cerrar_intento(intento_id, DB)
    except Exception as e:
        _error(e)


@app.get("/api/examenes/reporte")
def examen_reporte():
    return ex.reporte(DB)


@app.get("/api/examenes/preguntas")
def examen_preguntas(estado: Optional[str] = None, tema: Optional[str] = None):
    return {"preguntas": ex.listar_preguntas(estado, tema, DB)}


@app.post("/api/examenes/preguntas/{pregunta_id}/estado")
def examen_estado(pregunta_id: int, d: EstadoIn):
    try:
        ex.cambiar_estado(pregunta_id, d.estado, d.editado, DB)
        return {"ok": True}
    except Exception as e:
        _error(e)


# ------------------------------------------------------------------ proveedores y precios
class ProveedorIn(BaseModel):
    nombre: str = Field(max_length=80)
    contacto: str = Field(default="", max_length=80)
    telefono: str = Field(default="", max_length=30)
    dias_entrega: str = Field(default="", max_length=80)
    notas: str = Field(default="", max_length=300)


class PrecioIn(BaseModel):
    producto: str = Field(min_length=2, max_length=80)
    precio: float
    unidad_precio: str
    categoria: Optional[str] = Field(default=None, max_length=40)
    fecha: Optional[str] = None


class PorcionesIn(BaseModel):
    porciones: int


def _400(e: Exception):
    if isinstance(e, DatoInvalido):
        raise HTTPException(400, str(e))
    raise e


@app.get("/api/proveedores")
def api_proveedores():
    return {"proveedores": prov.listar(DB)}


@app.post("/api/proveedores")
def api_proveedor_crear(d: ProveedorIn):
    try:
        return {"id": prov.crear(d.nombre, d.contacto, d.telefono, d.dias_entrega, d.notas, DB)}
    except Exception as e:
        _400(e)


@app.get("/api/proveedores/{proveedor_id}")
def api_proveedor(proveedor_id: int):
    r = prov.detalle(proveedor_id, DB)
    if r is None:
        raise HTTPException(404, "No encuentro ese proveedor.")
    return r


class ProveedorEditIn(BaseModel):
    nombre: Optional[str] = Field(default=None, max_length=80)
    contacto: Optional[str] = Field(default=None, max_length=80)
    telefono: Optional[str] = Field(default=None, max_length=30)
    dias_entrega: Optional[str] = Field(default=None, max_length=80)
    notas: Optional[str] = Field(default=None, max_length=300)


@app.put("/api/proveedores/{proveedor_id}")
def api_proveedor_editar(proveedor_id: int, d: ProveedorEditIn):
    try:
        prov.editar(proveedor_id, d.nombre, d.contacto, d.telefono, d.dias_entrega, d.notas, DB)
        return {"ok": True}
    except Exception as e:
        _400(e)


@app.delete("/api/proveedores/{proveedor_id}")
def api_proveedor_quitar(proveedor_id: int):
    try:
        prov.quitar(proveedor_id, DB)
        return {"ok": True}
    except Exception as e:
        _400(e)


@app.delete("/api/proveedores/{proveedor_id}/productos/{producto_id}")
def api_proveedor_quitar_producto(proveedor_id: int, producto_id: int):
    try:
        prov.quitar_producto(proveedor_id, producto_id, DB)
        return {"ok": True}
    except Exception as e:
        _400(e)


@app.post("/api/proveedores/{proveedor_id}/precios")
def api_precio(proveedor_id: int, d: PrecioIn):
    try:
        return prov.poner_precio(proveedor_id, d.producto, d.precio, d.unidad_precio, d.categoria, d.fecha, DB)
    except Exception as e:
        _400(e)


@app.get("/api/precios/alertas")
def api_alertas_precio():
    return {"alertas": prov.alertas_de_precio(db_path=DB), "umbral_pct": prov.ALERTA_SUBIDA}


@app.get("/api/catalogo")
def api_catalogo():
    return {"productos": prov.catalogo(DB)}


# ------------------------------------------------------------------ inventario editable
class LoteIn(BaseModel):
    producto: str = Field(min_length=2, max_length=80)
    cantidad: float
    unidad: str = Field(max_length=20)
    fecha_ingreso: Optional[str] = None
    fecha_caducidad: Optional[str] = None
    id_lote: Optional[str] = Field(default=None, max_length=40)
    categoria: Optional[str] = Field(default=None, max_length=40)


class LoteEditIn(BaseModel):
    cantidad: Optional[float] = None
    unidad: Optional[str] = Field(default=None, max_length=20)
    fecha_ingreso: Optional[str] = None
    fecha_caducidad: Optional[str] = None
    quitar_caducidad: bool = False


class ProductoEditIn(BaseModel):
    nombre: Optional[str] = Field(default=None, max_length=80)
    categoria: Optional[str] = Field(default=None, max_length=40)
    tipo: Optional[str] = None
    vida_util_dias: Optional[int] = None


@app.get("/api/inventario/lotes")
def api_lotes(q: str = "", tipo: str = ""):
    return {"lotes": inv.lotes(q, tipo, db_path=DB)}


@app.post("/api/inventario/lotes")
def api_lote_crear(d: LoteIn):
    try:
        return inv.crear_lote(d.producto, d.cantidad, d.unidad, d.fecha_ingreso, d.fecha_caducidad, d.id_lote, d.categoria, DB)
    except Exception as e:
        _400(e)


@app.put("/api/inventario/lotes/{lote_id}")
def api_lote_editar(lote_id: int, d: LoteEditIn):
    try:
        inv.editar_lote(lote_id, d.cantidad, d.unidad, d.fecha_ingreso, d.fecha_caducidad, d.quitar_caducidad, DB)
        return {"ok": True}
    except Exception as e:
        _400(e)


@app.delete("/api/inventario/lotes/{lote_id}")
def api_lote_quitar(lote_id: int):
    try:
        inv.quitar_lote(lote_id, DB)
        return {"ok": True}
    except Exception as e:
        _400(e)


@app.get("/api/inventario/productos")
def api_productos(q: str = "", categoria: str = "", tipo: str = ""):
    return {"productos": inv.productos(q, categoria, tipo, DB), "categorias": inv.categorias(DB)}


@app.put("/api/inventario/productos/{producto_id}")
def api_producto_editar(producto_id: int, d: ProductoEditIn):
    try:
        inv.editar_producto(producto_id, d.nombre, d.categoria, d.tipo, d.vida_util_dias, DB)
        return {"ok": True}
    except Exception as e:
        _400(e)


@app.delete("/api/inventario/productos/{producto_id}")
def api_producto_quitar(producto_id: int):
    try:
        inv.quitar_producto(producto_id, DB)
        return {"ok": True}
    except Exception as e:
        _400(e)


@app.get("/api/inventario/productos/{producto_id}/precios")
def api_producto_precios(producto_id: int):
    """Quién vende este producto y a cuánto (del más barato al más caro)."""
    return {"precios": prov.precios_de_producto(producto_id, DB), "stock": prov.stock_de_producto(producto_id, DB)}


@app.get("/api/cambios")
def api_cambios(limite: int = 50):
    return {"cambios": inv.cambios(limite, DB)}


# ------------------------------------------------------------------ analisis del dueno (etapa E)
class DestinoIn(BaseModel):
    destino: str
    valor_estimado: Optional[float] = None


@app.get("/api/analisis")
def api_analisis(desde: Optional[str] = None, hasta: Optional[str] = None):
    try:
        return ana.resumen(desde, hasta, DB)
    except Exception as e:
        _400(e)


@app.post("/api/sobrantes/{sobrante_id}/destino")
def api_sobrante_destino(sobrante_id: int, d: DestinoIn):
    try:
        ana.registrar_destino_sobrante(sobrante_id, d.destino, d.valor_estimado, DB)
        return {"ok": True}
    except Exception as e:
        _400(e)


# ------------------------------------------------------------------ compras (costo real)
class CompraIn(BaseModel):
    proveedor_id: int
    producto: str = Field(min_length=2, max_length=80)
    cantidad: float
    unidad: str = Field(max_length=20)
    precio: float
    unidad_precio: str
    fecha: Optional[str] = None
    vence: Optional[str] = None
    factura: str = Field(default="", max_length=60)
    notas: str = Field(default="", max_length=300)
    crear_lote: bool = True
    actualizar_precio: bool = True
    categoria: Optional[str] = Field(default=None, max_length=40)


@app.get("/api/compras")
def api_compras(desde: Optional[str] = None, hasta: Optional[str] = None, proveedor_id: Optional[int] = None):
    try:
        return com.listar(desde, hasta, proveedor_id, db_path=DB)
    except Exception as e:
        _400(e)


@app.post("/api/compras")
def api_compra_crear(d: CompraIn):
    try:
        return com.registrar(d.proveedor_id, d.producto, d.cantidad, d.unidad, d.precio, d.unidad_precio, d.fecha, d.vence,
                             d.factura, d.notas, d.crear_lote, d.actualizar_precio, d.categoria, DB)
    except Exception as e:
        _400(e)


@app.delete("/api/compras/{compra_id}")
def api_compra_anular(compra_id: int):
    try:
        return com.anular(compra_id, DB)
    except Exception as e:
        _400(e)


@app.get("/api/analisis/costo-real")
def api_costo_real(desde: Optional[str] = None, hasta: Optional[str] = None):
    try:
        return com.costo_real(desde, hasta, DB)
    except Exception as e:
        _400(e)


# ------------------------------------------------------------------ conteo de inventario (fin de mes)
class ConteoIn(BaseModel):
    fecha: Optional[str] = None
    incluye_limpieza: bool = False
    notas: str = Field(default="", max_length=300)


class CantidadIn(BaseModel):
    producto_id: int
    cantidad: Optional[float] = None


class CantidadesIn(BaseModel):
    cantidades: List[CantidadIn]


class ProductoConteoIn(BaseModel):
    producto: str = Field(min_length=2, max_length=80)
    cantidad: float
    unidad: str = Field(max_length=20)


class CierreIn(BaseModel):
    cerrado_por: str = Field(max_length=80)
    ajustar_inventario: bool = True
    sin_contar_igual: bool = False


@app.get("/api/conteos")
def api_conteos():
    return {"conteos": cnt.listar(DB)}


@app.post("/api/conteos")
def api_conteo_crear(d: ConteoIn):
    try:
        return cnt.crear(d.fecha, d.incluye_limpieza, d.notas, DB)
    except Exception as e:
        _400(e)


@app.get("/api/conteos/{conteo_id}")
def api_conteo(conteo_id: int):
    r = cnt.detalle(conteo_id, DB)
    if r is None:
        raise HTTPException(404, "No encuentro ese conteo.")
    return r


@app.put("/api/conteos/{conteo_id}/cantidades")
def api_conteo_contar(conteo_id: int, d: CantidadesIn):
    try:
        return cnt.contar(conteo_id, [c.model_dump() for c in d.cantidades], DB)
    except Exception as e:
        _400(e)


@app.post("/api/conteos/{conteo_id}/productos")
def api_conteo_agregar(conteo_id: int, d: ProductoConteoIn):
    try:
        return cnt.agregar_producto(conteo_id, d.producto, d.cantidad, d.unidad, DB)
    except Exception as e:
        _400(e)


@app.post("/api/conteos/{conteo_id}/cerrar")
def api_conteo_cerrar(conteo_id: int, d: CierreIn):
    try:
        return cnt.cerrar(conteo_id, d.cerrado_por, d.ajustar_inventario, d.sin_contar_igual, DB)
    except Exception as e:
        _400(e)


@app.delete("/api/conteos/{conteo_id}")
def api_conteo_anular(conteo_id: int):
    try:
        cnt.anular(conteo_id, DB)
        return {"ok": True}
    except Exception as e:
        _400(e)


# ------------------------------------------------------------------ informe del turno (etapa F)
class ProducidoIn(BaseModel):
    receta_id: Optional[str] = None
    plato: str = Field(default="", max_length=120)
    servicio: Optional[str] = None
    producido: int = 0
    vendido: int = 0
    recibido: Optional[int] = None  # lo cuenta OTRA persona (mostrador, despacho)


class IncidenciaIn(BaseModel):
    tipo: str = "otro"
    descripcion: str = Field(max_length=1000)


class InformeIn(BaseModel):
    fecha: str
    turno: str
    chef_id: Optional[str] = None
    personal: List[str] = []
    producido: Optional[List[ProducidoIn]] = None
    incidencias: List[IncidenciaIn] = []
    observaciones: str = Field(default="", max_length=1000)


class FirmaIn(BaseModel):
    fecha: str
    turno: str
    firmado_por: str = Field(max_length=80)


class MovimientoIn(BaseModel):
    fecha: str
    turno: str
    tipo: str
    producto: str = Field(min_length=2, max_length=80)
    cantidad: float
    unidad: str = Field(max_length=20)
    entrego: str = Field(default="", max_length=80)
    recibio: str = Field(default="", max_length=80)
    descontar_inventario: bool = True


class SalidaIn(BaseModel):
    fecha: str
    turno: str
    tipo: str
    kg: float
    nota: str = Field(default="", max_length=200)
    persona: str = Field(default="", max_length=80)
    producto: Optional[str] = Field(default=None, max_length=80)


class MermaTurnoIn(BaseModel):
    fecha: str
    turno: str
    producto: str = Field(min_length=2, max_length=80)
    cantidad: float
    unidad: str = Field(max_length=20)
    motivo: str = Field(max_length=80)
    costo: Optional[float] = None


class EstandarIn(BaseModel):
    peso_unidad_g: Optional[float] = None
    perdida_normal_pct: float = 3.0
    tolerancia_pct: float = 2.0
    notas: str = Field(default="", max_length=300)


class PesoIn(BaseModel):
    kg_por_unidad: Optional[float] = None


@app.get("/api/balance")
def api_balance(fecha: str, turno: str):
    """Balance del turno con lo producido del informe (si el chef lo corrigio) o de las ventas."""
    try:
        return tur.abrir(fecha, turno, DB)["datos"]["balance"]
    except Exception as e:
        _400(e)


@app.get("/api/balance/tendencia")
def api_balance_tendencia(desde: Optional[str] = None, hasta: Optional[str] = None):
    return bal.tendencia(desde or None, hasta or None, DB)


@app.post("/api/balance/movimientos")
def api_balance_mov(d: MovimientoIn):
    try:
        return bal.anotar_movimiento(d.fecha, d.turno, d.tipo, d.producto, d.cantidad, d.unidad, d.entrego, d.recibio, d.descontar_inventario, DB)
    except Exception as e:
        _400(e)


@app.delete("/api/balance/movimientos/{mov_id}")
def api_balance_mov_quitar(mov_id: int):
    try:
        bal.quitar_movimiento(mov_id, DB)
        return {"ok": True}
    except Exception as e:
        _400(e)


@app.post("/api/balance/salidas")
def api_balance_salida(d: SalidaIn):
    try:
        return bal.anotar_salida(d.fecha, d.turno, d.tipo, d.kg, d.nota, d.persona, d.producto, DB)
    except Exception as e:
        _400(e)


@app.delete("/api/balance/salidas/{salida_id}")
def api_balance_salida_quitar(salida_id: int):
    try:
        bal.quitar_salida(salida_id, DB)
        return {"ok": True}
    except Exception as e:
        _400(e)


@app.post("/api/balance/mermas")
def api_balance_merma(d: MermaTurnoIn):
    try:
        return bal.anotar_merma(d.fecha, d.turno, d.producto, d.cantidad, d.unidad, d.motivo, d.costo, DB)
    except Exception as e:
        _400(e)


@app.get("/api/recetas/{receta_id}/estandar")
def api_estandar(receta_id: str):
    return bal.estandar(receta_id, DB)


@app.put("/api/recetas/{receta_id}/estandar")
def api_estandar_guardar(receta_id: str, d: EstandarIn):
    try:
        bal.guardar_estandar(receta_id, d.peso_unidad_g, d.perdida_normal_pct, d.tolerancia_pct, d.notas, DB)
        return {"ok": True}
    except Exception as e:
        _400(e)


@app.put("/api/inventario/productos/{producto_id}/peso")
def api_producto_peso(producto_id: int, d: PesoIn):
    try:
        bal.poner_kg_por_unidad(producto_id, d.kg_por_unidad, DB)
        return {"ok": True}
    except Exception as e:
        _400(e)


@app.get("/api/turnos")
def api_turnos(desde: Optional[str] = None, hasta: Optional[str] = None):
    return {"informes": tur.listar(desde, hasta, DB)}


@app.get("/api/turnos/informe")
def api_turno_abrir(fecha: str, turno: str):
    try:
        return tur.abrir(fecha, turno, DB)
    except Exception as e:
        _400(e)


@app.put("/api/turnos/informe")
def api_turno_guardar(d: InformeIn):
    try:
        prod = [p.model_dump() for p in d.producido] if d.producido is not None else None
        return tur.guardar(d.fecha, d.turno, d.chef_id, d.personal, prod, [i.model_dump() for i in d.incidencias], d.observaciones, DB)
    except Exception as e:
        _400(e)


@app.post("/api/turnos/informe/firmar")
def api_turno_firmar(d: FirmaIn):
    try:
        return tur.firmar(d.fecha, d.turno, d.firmado_por, DB)
    except Exception as e:
        _400(e)


# ------------------------------------------------------------------ recetas
@app.get("/api/recetas")
def api_recetas(q: str = "", categoria: str = ""):
    return {"recetas": rec.listar(q, categoria, DB), "categorias": rec.categorias(DB)}


@app.get("/api/recetas/{receta_id}")
def api_receta(receta_id: str):
    r = rec.ficha(receta_id, DB)
    if r is None:
        raise HTTPException(404, "No encuentro esa receta.")
    return r


@app.put("/api/recetas/{receta_id}/porciones")
def api_receta_porciones(receta_id: str, d: PorcionesIn):
    try:
        rec.poner_porciones(receta_id, d.porciones, DB)
        return {"ok": True}
    except Exception as e:
        _400(e)


# ------------------------------------------------------------------ menu y costos (etapa D)
def _lista(txt: str) -> List[str]:
    return [x.strip() for x in txt.split(",") if x.strip()]


def _menu_400(e: Exception):
    if isinstance(e, men.MenuError):
        raise HTTPException(400, str(e))
    raise e


@app.get("/api/menu/costos")
def api_menu_costos():
    return men.costo_por_persona(DB)


@app.get("/api/menu/sugerencia")
def api_menu_sugerencia(comidas: str = "desayuno,almuerzo,merienda", tope: Optional[float] = None, sin: str = "",
                        dias: int = 1, por_vencer: bool = True, semilla: int = 0):
    try:
        return men.armar_menu(_lista(comidas), tope, _lista(sin), dias, por_vencer, semilla=semilla, db_path=DB)
    except Exception as e:
        _menu_400(e)


@app.get("/api/menu/cocinar")
def api_menu_cocinar(dias: int = 1, sin: str = ""):
    if not 0 <= dias <= 30:
        raise HTTPException(400, "Elige entre 0 y 30 días.")
    try:
        return men.que_cocinar(dias, excluir=_lista(sin), db_path=DB)
    except Exception as e:
        _menu_400(e)


@app.get("/api/menu/sobrantes")
def api_menu_sobrantes():
    return men.aprovechar_sobrantes(db_path=DB)


@app.get("/api/menu/alergenos")
def api_menu_alergenos():
    return {"alergenos": list(men.ALERGENOS), "comidas": list(men.PLANTILLAS)}


# ------------------------------------------------------------------ manuales (ver e imprimir)
_SQL_MANUALES = (
    "SELECT min(d.id) AS id, d.nombre, d.tipo, length(t.contenido_completo) AS letras "
    "FROM DocumentosRAG d JOIN DocumentosTexto t ON t.documento_id=d.id "
    "WHERE d.estado='activo' AND d.extension IN ('.md','.txt') AND length(coalesce(t.contenido_completo,''))>200 "
    "GROUP BY d.nombre ORDER BY d.nombre"
)


def _leer_archivo(archivo: UploadFile) -> bytes:
    datos = archivo.file.read(carga.MAX_BYTES + 1)
    if len(datos) > carga.MAX_BYTES:
        raise HTTPException(400, "El archivo pesa más de 5 MB.")
    return datos


@app.post("/api/recetas/cargar")
def api_recetas_cargar(archivo: UploadFile = File(...)):
    try:
        return carga.cargar_recetas_csv(_leer_archivo(archivo), archivo.filename or "recetas.csv", DB)
    except carga.CargaError as e:
        raise HTTPException(400, str(e))


@app.post("/api/manuales/cargar")
def api_manuales_cargar(archivo: UploadFile = File(...)):
    try:
        return carga.cargar_manual(_leer_archivo(archivo), archivo.filename or "manual.md", DB)
    except carga.CargaError as e:
        raise HTTPException(400, str(e))


@app.get("/api/manuales")
def manuales():
    return {"manuales": _q(_SQL_MANUALES)}


@app.get("/api/manuales/{doc_id}")
def manual(doc_id: int):
    filas = _q("SELECT d.id, d.nombre, t.contenido_completo AS texto FROM DocumentosRAG d "
               "JOIN DocumentosTexto t ON t.documento_id=d.id WHERE d.id=? AND d.estado='activo' "
               "AND d.extension IN ('.md','.txt')", (doc_id,))
    if not filas:
        raise HTTPException(404, "No encuentro ese manual.")
    return filas[0]


# ------------------------------------------------------------------ pantalla web
_DIST = RAIZ / "web" / "dist"
if _DIST.exists():
    app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/{ruta:path}")
    def spa(ruta: str):
        archivo = (_DIST / ruta).resolve()
        if ruta and archivo.is_file() and _DIST in archivo.parents:
            return FileResponse(archivo)
        return FileResponse(_DIST / "index.html")
