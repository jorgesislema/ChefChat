"""Esquema de la etapa B: tablas nuevas y columna `tipo` del catalogo.

`asegurar_esquema` se puede llamar muchas veces: solo crea lo que falta.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from core.normalizar import clave

DB_PATH = str(Path(__file__).resolve().parent.parent / "chefchat.db")

CATEGORIAS_LIMPIEZA = {"limpieza"}

_TABLAS = """
CREATE TABLE IF NOT EXISTS Proveedores (
    id INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE COLLATE NOCASE,
    contacto TEXT, telefono TEXT, dias_entrega TEXT, notas TEXT,
    activo INTEGER NOT NULL DEFAULT 1,
    es_demo INTEGER NOT NULL DEFAULT 0);

CREATE TABLE IF NOT EXISTS ProveedorProductos (
    id INTEGER PRIMARY KEY,
    proveedor_id INTEGER NOT NULL REFERENCES Proveedores(id),
    producto_id INTEGER NOT NULL REFERENCES Catalogo(id),
    precio REAL NOT NULL CHECK (precio >= 0),
    unidad_precio TEXT NOT NULL,
    fecha TEXT NOT NULL,
    es_demo INTEGER NOT NULL DEFAULT 0,
    UNIQUE (proveedor_id, producto_id, fecha));
CREATE INDEX IF NOT EXISTS ix_pp_producto ON ProveedorProductos(producto_id, fecha);

CREATE TABLE IF NOT EXISTS RecetaIngredientes (
    id INTEGER PRIMARY KEY,
    receta_id TEXT NOT NULL,
    producto_id INTEGER REFERENCES Catalogo(id),
    ingrediente TEXT NOT NULL,
    cantidad REAL,
    unidad TEXT,
    UNIQUE (receta_id, ingrediente));
CREATE INDEX IF NOT EXISTS ix_ri_receta ON RecetaIngredientes(receta_id);

CREATE TABLE IF NOT EXISTS Ventas (
    id INTEGER PRIMARY KEY,
    fecha TEXT NOT NULL,
    servicio TEXT NOT NULL,
    plato TEXT NOT NULL,
    receta_id TEXT,
    producido INTEGER NOT NULL CHECK (producido >= 0),
    vendido INTEGER NOT NULL CHECK (vendido >= 0),
    precio_unitario REAL NOT NULL,
    es_demo INTEGER NOT NULL DEFAULT 0,
    UNIQUE (fecha, servicio, plato));
CREATE INDEX IF NOT EXISTS ix_ventas_fecha ON Ventas(fecha);

CREATE TABLE IF NOT EXISTS InformesTurno (
    id INTEGER PRIMARY KEY,
    fecha TEXT NOT NULL,
    turno TEXT NOT NULL,
    chef_id TEXT REFERENCES Trabajadores(id_empleado),
    personal TEXT,            -- ids separados por coma
    producido TEXT,           -- texto libre o json
    merma_texto TEXT,
    merma_recuperada_texto TEXT,
    incidencias TEXT,
    observaciones TEXT,
    estado TEXT NOT NULL DEFAULT 'borrador',   -- borrador | firmado
    creado TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (fecha, turno));

-- Compras recibidas: base del costo REAL de alimentos (lo que se gasto), frente al costo teorico (lo que debio costar)
CREATE TABLE IF NOT EXISTS Compras (
    id INTEGER PRIMARY KEY,
    fecha TEXT NOT NULL,
    proveedor_id INTEGER NOT NULL REFERENCES Proveedores(id),
    producto_id INTEGER NOT NULL REFERENCES Catalogo(id),
    cantidad REAL NOT NULL CHECK (cantidad > 0),
    unidad TEXT NOT NULL,
    precio REAL NOT NULL CHECK (precio >= 0),      -- precio por unidad_precio
    unidad_precio TEXT NOT NULL,                     -- kg | l | unidad
    total REAL NOT NULL CHECK (total >= 0),
    lote_id INTEGER,                                 -- lote que se creo en el inventario (si se creo)
    cantidad_lote REAL,                              -- cantidad con la que nacio ese lote (para saber si se uso)
    factura TEXT,
    notas TEXT,
    es_demo INTEGER NOT NULL DEFAULT 0,
    creado TEXT NOT NULL DEFAULT (datetime('now', 'localtime')));
CREATE INDEX IF NOT EXISTS ix_compras_fecha ON Compras(fecha);

-- Conteo fisico de inventario (normalmente a fin de mes). Con dos conteos cerrados el costo real es exacto:
-- costo = inventario inicial + compras - inventario final
CREATE TABLE IF NOT EXISTS Conteos (
    id INTEGER PRIMARY KEY,
    fecha TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'abierto',      -- abierto | cerrado
    incluye_limpieza INTEGER NOT NULL DEFAULT 0,
    notas TEXT,
    cerrado_por TEXT,
    cerrado_en TEXT,
    ajusto_inventario INTEGER NOT NULL DEFAULT 0,
    valor_sistema REAL,                          -- se guardan al cerrar
    valor_contado REAL,
    es_demo INTEGER NOT NULL DEFAULT 0,
    creado TEXT NOT NULL DEFAULT (datetime('now', 'localtime')));
CREATE INDEX IF NOT EXISTS ix_conteos_fecha ON Conteos(fecha);

CREATE TABLE IF NOT EXISTS ConteoLineas (
    id INTEGER PRIMARY KEY,
    conteo_id INTEGER NOT NULL REFERENCES Conteos(id),
    producto_id INTEGER NOT NULL REFERENCES Catalogo(id),
    unidad TEXT NOT NULL,                        -- kg | l | unidad (la del precio)
    cantidad_sistema REAL NOT NULL,
    cantidad_contada REAL,                       -- NULL = aun no contado
    precio REAL,                                 -- precio por unidad (el mas barato vigente al crear el conteo)
    UNIQUE (conteo_id, producto_id));

-- Balance del turno: lo «normal» de cada receta (se mide en la cocina real pesando 3 a 5 tandas)
CREATE TABLE IF NOT EXISTS EstandaresReceta (
    receta_id TEXT PRIMARY KEY,
    peso_unidad_g REAL CHECK (peso_unidad_g IS NULL OR peso_unidad_g > 0),
    perdida_normal_pct REAL NOT NULL DEFAULT 3 CHECK (perdida_normal_pct >= 0 AND perdida_normal_pct < 60),
    tolerancia_pct REAL NOT NULL DEFAULT 2 CHECK (tolerancia_pct > 0 AND tolerancia_pct <= 30),
    notas TEXT,
    actualizado TEXT NOT NULL DEFAULT (datetime('now', 'localtime')));

-- Lo que bodega entrega al turno (o recibe de vuelta). Lo anota BODEGA, no el turno.
CREATE TABLE IF NOT EXISTS MovimientosTurno (
    id INTEGER PRIMARY KEY,
    fecha TEXT NOT NULL,
    turno TEXT NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo IN ('entrega', 'devolucion')),
    producto_id INTEGER NOT NULL REFERENCES Catalogo(id),
    cantidad REAL NOT NULL CHECK (cantidad > 0),
    unidad TEXT NOT NULL,
    entrego TEXT, recibio TEXT,
    desconto_inventario INTEGER NOT NULL DEFAULT 1,
    es_demo INTEGER NOT NULL DEFAULT 0,
    creado TEXT NOT NULL DEFAULT (datetime('now', 'localtime')));
CREATE INDEX IF NOT EXISTS ix_mov_turno ON MovimientosTurno(fecha, turno);

-- Lo que sale del turno sin ser venta ni merma: comida del personal, residuo de limpieza, muestras
CREATE TABLE IF NOT EXISTS SalidasTurno (
    id INTEGER PRIMARY KEY,
    fecha TEXT NOT NULL,
    turno TEXT NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo IN ('comida_personal', 'residuo_limpieza', 'muestra', 'otro')),
    kg REAL NOT NULL CHECK (kg > 0),
    producto_id INTEGER REFERENCES Catalogo(id),
    nota TEXT, persona TEXT,
    es_demo INTEGER NOT NULL DEFAULT 0,
    creado TEXT NOT NULL DEFAULT (datetime('now', 'localtime')));
CREATE INDEX IF NOT EXISTS ix_salidas_turno ON SalidasTurno(fecha, turno);

CREATE TABLE IF NOT EXISTS Bitacora_Diaria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    categoria TEXT NOT NULL,
    descripcion TEXT NOT NULL);

-- Registro de cambios hechos desde la pantalla (quien cambio que, y desde que valor)
CREATE TABLE IF NOT EXISTS Cambios (
    id INTEGER PRIMARY KEY,
    fecha TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    entidad TEXT NOT NULL,     -- proveedor, precio, producto, lote, sobrante
    accion TEXT NOT NULL,      -- crear, cambiar, quitar
    detalle TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_cambios_fecha ON Cambios(fecha);
"""


def registrar_cambio(conn: sqlite3.Connection, entidad: str, accion: str, detalle: str) -> None:
    """Anota un cambio hecho por el usuario. Usa la misma conexion: se guarda junto con el cambio."""
    conn.execute("INSERT INTO Cambios (entidad, accion, detalle) VALUES (?,?,?)", (entidad, accion, detalle[:500]))


def tipo_por_categoria(categoria: str | None) -> str:
    """'limpieza' si la categoria es de limpieza; si no, 'alimento'."""
    return "limpieza" if clave(categoria) in CATEGORIAS_LIMPIEZA else "alimento"


def asegurar_esquema(db_path: str = DB_PATH) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(_TABLAS)
        cols = {r[1] for r in conn.execute("PRAGMA table_info(Catalogo)")}
        if "origen" not in cols:  # 'auto_receta' = producto creado automaticamente desde las recetas
            conn.execute("ALTER TABLE Catalogo ADD COLUMN origen TEXT")
        pp = {r[1] for r in conn.execute("PRAGMA table_info(ProveedorProductos)")}
        if "quitado" not in pp:  # 1 = el proveedor ya no vende este producto (se conserva el historial)
            conn.execute("ALTER TABLE ProveedorProductos ADD COLUMN quitado INTEGER NOT NULL DEFAULT 0")
        if "kg_por_unidad" not in cols:  # peso de 1 unidad (huevo, pieza) o de 1 litro; NULL = sin dato
            conn.execute("ALTER TABLE Catalogo ADD COLUMN kg_por_unidad REAL")
        mermas = {r[1] for r in conn.execute("PRAGMA table_info(Mermas)")}
        if mermas and "turno" not in mermas:  # merma pesada de cada turno (NULL = merma del dia sin turno)
            conn.execute("ALTER TABLE Mermas ADD COLUMN turno TEXT")
        if mermas and "es_demo" not in mermas:
            conn.execute("ALTER TABLE Mermas ADD COLUMN es_demo INTEGER NOT NULL DEFAULT 0")
        it = {r[1] for r in conn.execute("PRAGMA table_info(InformesTurno)")}
        for col, tipo in (("datos_json", "TEXT"), ("firmado_por", "TEXT"), ("firmado_en", "TEXT"), ("actualizado", "TEXT")):
            if col not in it:  # datos_json = foto de los numeros al firmar (el informe firmado ya no cambia)
                conn.execute(f"ALTER TABLE InformesTurno ADD COLUMN {col} {tipo}")
        sb = {r[1] for r in conn.execute("PRAGMA table_info(SobrantesReutilizables)")}
        if sb and "valor_estimado" not in sb:  # dinero que se recupero al reutilizar (lo escribe el chef)
            conn.execute("ALTER TABLE SobrantesReutilizables ADD COLUMN valor_estimado REAL")
        if sb and "fecha_destino" not in sb:
            conn.execute("ALTER TABLE SobrantesReutilizables ADD COLUMN fecha_destino TEXT")
        if "tipo" not in cols:
            conn.execute("ALTER TABLE Catalogo ADD COLUMN tipo TEXT NOT NULL DEFAULT 'alimento'")
            # solo la primera vez: despues el dueno puede corregir el tipo a mano
            for pid, cat in conn.execute("SELECT id, categoria FROM Catalogo").fetchall():
                conn.execute("UPDATE Catalogo SET tipo=? WHERE id=?", (tipo_por_categoria(cat), pid))
        conn.commit()
    finally:
        conn.close()
