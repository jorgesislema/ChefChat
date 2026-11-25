"""Etapa B: datos nuevos en chefchat.db (repetible, con copia de respaldo).

1. Crea tablas y la columna tipo (alimento / limpieza).
2. Une cada ingrediente de las recetas con un producto del catalogo (RecetaIngredientes).
3. DATOS FICTICIOS (es_demo=1): proveedores, precios con historial y ventas de 90 dias.

Uso:  python scripts/etapa_b_datos.py
Las filas es_demo=1 se borran y se vuelven a crear cada vez; nada real se toca.
"""

from __future__ import annotations

import hashlib
import random
import re
import shutil
import sqlite3
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from core.normalizar import buscar_producto_id, clave, nombre_canonico  # noqa: E402
from data.esquema import asegurar_esquema  # noqa: E402
from data.vinculos import GRATIS, paso_ingredientes  # noqa: E402

HOY = date(2026, 11, 24)  # fecha ancla de los datos ficticios


# --- precios ficticios (por kg, litro o unidad), segun categoria --------------------------------
PRECIO_BASE = {
    "Carnes": 9.0, "Embutidos": 12.0, "Frutas": 1.8, "Vegetales": 1.4, "Verduras": 1.4, "Hierbas": 3.0,
    "Lácteos": 4.0, "Mariscos": 14.0, "Pescados": 11.0, "Proteinas": 6.5, "Cereales": 2.2, "Granos": 1.6,
    "Secos": 2.0, "Panaderia": 1.2, "Aceites": 6.0, "Cocina": 3.5, "Condimentos": 2.5, "Bebidas": 8.0,
    "Limpieza": 4.0, "Sin clasificar": 3.0, "General": 3.0,
}
PROVEEDORES = [
    ("Mercado Mayorista Central", "Rosa Quishpe", "0991000001", "Lunes, miércoles y viernes",
     {"Vegetales", "Verduras", "Frutas", "Hierbas", "Sin clasificar", "General"}),
    ("Carnes del Valle", "Marco Andrade", "0991000002", "Martes y jueves",
     {"Carnes", "Embutidos", "Proteinas"}),
    ("Mariscos Pacífico", "Lucía Cedeño", "0991000003", "Miércoles y sábado", {"Mariscos", "Pescados"}),
    ("Lácteos La Pradera", "Iván Toapanta", "0991000004", "Lunes a sábado", {"Lácteos", "Proteinas"}),
    ("Distribuidora Andina", "Sofía Naranjo", "0991000005", "Martes y viernes",
     {"Secos", "Cereales", "Granos", "Aceites", "Condimentos", "Cocina", "Bebidas", "Panaderia", "Proteinas",
      "Carnes", "Sin clasificar", "Verduras", "Vegetales", "Frutas", "Lácteos"}),
    ("Limpieza Total", "Pablo Mena", "0991000006", "Jueves", {"Limpieza"}),
]
PRODUCTO_CON_SUBIDA = "Pollo"  # sube 18 % en el ultimo mes (para probar la alerta de precios)
FECHAS_PRECIO = [date(2026, 9, 1), date(2026, 10, 1), date(2026, 11, 1)]

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
VENTAS_POR_SERVICIO = {"desayuno": (8, 25), "almuerzo": (15, 40), "merienda": (6, 18), "a_la_carta": (3, 12), "cena": (5, 20)}


def _unidad_precio(conn: sqlite3.Connection, pid: int) -> str:
    """Unidad del precio: la del inventario; si no hay stock, la que mas se usa en las recetas (g->kg, ml->l)."""
    from core.unidades import familia
    fila = conn.execute("SELECT unidad FROM Inventario WHERE producto_id=? AND unidad IS NOT NULL LIMIT 1", (pid,)).fetchone()
    if fila:
        return familia(fila[0]) or "unidad"
    usos = Counter(familia(u) for (u,) in conn.execute("SELECT unidad FROM RecetaIngredientes WHERE producto_id=?", (pid,)))
    usos.pop(None, None)
    return usos.most_common(1)[0][0] if usos else "kg"


















def _jitter(clave_txt: str, amp: float) -> float:
    """Numero estable entre 1-amp y 1+amp para un texto (misma entrada, mismo resultado)."""
    h = int(hashlib.sha1(clave_txt.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return 1 + (h * 2 - 1) * amp


def paso_proveedores(conn: sqlite3.Connection) -> dict:
    conn.execute("DELETE FROM ProveedorProductos WHERE es_demo=1")
    conn.execute("DELETE FROM Proveedores WHERE es_demo=1")
    ids = {}
    for nombre, contacto, tel, dias, _cats in PROVEEDORES:
        cur = conn.execute("INSERT INTO Proveedores (nombre, contacto, telefono, dias_entrega, notas, es_demo) "
                           "VALUES (?,?,?,?,?,1)", (nombre, contacto, tel, dias, "DATO FICTICIO de demostración"))
        ids[nombre] = cur.lastrowid
    precios = 0
    for pid, nombre_p, cat in conn.execute("SELECT id, nombre, categoria FROM Catalogo").fetchall():
        provs = [p for p in PROVEEDORES if cat in p[4]]
        if not provs:
            continue
        # el primero que vende la categoria es el principal; si hay otro, tambien ofrece el producto
        elegidos = provs[:1] + ([provs[-1]] if len(provs) > 1 and _jitter(nombre_p + "2", 1) > 1 else [])
        base = PRECIO_BASE.get(cat, 3.0) * _jitter(nombre_p, 0.35)
        unidad = _unidad_precio(conn, pid)
        if unidad == "unidad" and nombre_p in PESOS_TIPICOS:  # PRECIO_BASE es por kg: una yema no cuesta lo de un kg
            base = max(base * PESOS_TIPICOS[nombre_p], 0.01)
        for prov in dict.fromkeys(e[0] for e in elegidos):
            factor_prov = _jitter(prov + nombre_p, 0.12)
            for i, f in enumerate(FECHAS_PRECIO):
                precio = base * factor_prov * _jitter(f"{prov}{nombre_p}{f}", 0.03)
                if nombre_p == PRODUCTO_CON_SUBIDA and prov == "Carnes del Valle" and i == len(FECHAS_PRECIO) - 1:
                    precio = base * factor_prov * 1.18
                conn.execute("INSERT OR IGNORE INTO ProveedorProductos (proveedor_id, producto_id, precio, unidad_precio, fecha, es_demo) "
                             "VALUES (?,?,?,?,?,1)", (ids[prov], pid, round(precio, 2), unidad, f.isoformat()))
                precios += 1
    return {"proveedores": len(ids), "precios": precios}


# Carta de demostracion: SOLO platos que tienen receta (si no, no se puede saber cuanto cuestan).
SERVICIO_POR_CATEGORIA = {"sopas": "almuerzo", "platos fuertes": "almuerzo", "ensaladas y guarniciones": "almuerzo",
                          "entrantes": "cena", "postres": "merienda", "bebidas": "desayuno"}
PLATOS_POR_CATEGORIA = {"sopas": 4, "platos fuertes": 7, "ensaladas y guarniciones": 3, "entrantes": 4, "postres": 4, "bebidas": 3}


def _carta(conn: sqlite3.Connection) -> list[tuple]:
    """[(servicio, plato, receta_id, precio, dias_de_venta)]. El precio es ficticio: costo por plato x un margen de 2,4 a 4,4."""
    carta, vistos = [], set()
    # platos del menu semanal que si tienen receta (conservan su precio del menu)
    for serv, plato, rid, precio in conn.execute(
            "SELECT DISTINCT lower(m.Tipo_Servicio), r.nombre, m.receta_id, m.Precio_Venta_USD FROM MenuSemanalPro m "
            "JOIN RecetasRAG r ON r.id_receta=m.receta_id"):
        if rid not in vistos:
            vistos.add(rid)
            carta.append((serv, plato, rid, precio))
    por_cat: dict[str, list] = {}
    for rid, nombre, cat, costo in conn.execute("SELECT id_receta, nombre, categoria, costo FROM RecetasRAG WHERE costo IS NOT NULL AND costo>0 ORDER BY id_receta"):
        if clave(cat) in PLATOS_POR_CATEGORIA and rid not in vistos:
            por_cat.setdefault(clave(cat), []).append((rid, nombre, costo))
    for cat, n in PLATOS_POR_CATEGORIA.items():
        lista = por_cat.get(cat, [])
        paso = max(len(lista) // n, 1)
        for rid, nombre, costo in lista[::paso][:n]:
            factor = 2.4 + _jitter(rid, 1)  # entre 2,4 y 4,4 veces el costo
            precio = max(round(costo * factor * 4) / 4, round(costo * 4) / 4 + 0.25)  # a 0,25 y siempre mayor que el costo
            carta.append((SERVICIO_POR_CATEGORIA[cat], nombre, rid, precio))
    salida = []
    for serv, plato, rid, precio in carta:
        rng_p = random.Random(f"dias-{rid}")
        dias = set(rng_p.sample(range(7), 4))  # cada plato se vende 4 dias a la semana
        salida.append((serv, plato, rid, precio, dias))
    return salida


def paso_ventas(conn: sqlite3.Connection) -> dict:
    conn.execute("DELETE FROM Ventas WHERE es_demo=1")
    carta = _carta(conn)
    por_dia: dict[int, list] = {}
    for serv, plato, rid, precio, dias in carta:
        for d in dias:
            por_dia.setdefault(d, []).append((serv, plato, rid, precio))
    rng = random.Random(2026)
    filas = 0
    for n in range(90, 0, -1):
        d = HOY - timedelta(days=n)
        for serv, plato, rid, precio in por_dia.get(d.weekday(), []):
            lo, hi = VENTAS_POR_SERVICIO.get(serv, (5, 15))
            factor = 1.3 if d.weekday() >= 4 else 1.0  # viernes a domingo se vende mas
            vendido = int(rng.randint(lo, hi) * factor)
            producido = vendido + rng.randint(0, max(2, vendido // 6))  # siempre se produce un poco de mas
            cur = conn.execute("INSERT OR IGNORE INTO Ventas (fecha, servicio, plato, receta_id, producido, vendido, precio_unitario, es_demo) "
                               "VALUES (?,?,?,?,?,?,?,1)", (d.isoformat(), serv, plato, rid, producido, vendido, precio))
            filas += cur.rowcount
    return {"filas": filas}


def paso_compras(conn: sqlite3.Connection) -> dict:
    """Compras FICTICIAS dos veces por semana. Cada semana se compra lo que pide la produccion de esa semana
    (costo por plato x producido) mas entre 6 % y 14 % de «fuga», repartido entre los productos que usan las recetas
    vendidas. No crea lotes: el inventario de demostracion ya tiene los suyos."""
    from core.unidades import convertir
    conn.execute("DELETE FROM Compras WHERE es_demo=1")  # la tabla la crea asegurar_esquema() en main()
    costos = {r[0]: r[1] for r in conn.execute("SELECT id_receta, costo FROM RecetasRAG WHERE costo IS NOT NULL")}
    precios: dict[int, tuple] = {}
    for pid, prov_id, precio, unidad, cat in conn.execute(
            "SELECT pp.producto_id, pp.proveedor_id, pp.precio, pp.unidad_precio, k.categoria FROM ProveedorProductos pp "
            "JOIN Proveedores p ON p.id=pp.proveedor_id JOIN Catalogo k ON k.id=pp.producto_id "
            "WHERE p.activo=1 AND pp.quitado=0 ORDER BY pp.fecha"):
        # los precios ficticios «por unidad» de especias y secos no tienen sentido (un clavo de olor a $2): no se compran en la demo
        if unidad == "unidad" and clave(cat) not in ("proteinas", "frutas", "vegetales", "verduras", "panaderia", "lacteos"):
            continue
        actual = precios.get(pid)
        if actual is None or precio < actual[1]:
            precios[pid] = (prov_id, precio, unidad)
    usos: dict[str, list] = {}
    for rid, pid, cant, uni in conn.execute("SELECT receta_id, producto_id, cantidad, unidad FROM RecetaIngredientes WHERE producto_id IS NOT NULL"):
        if pid in precios and cant:
            eq = convertir(cant, uni, precios[pid][2])
            if eq:
                usos.setdefault(rid, []).append((pid, eq * precios[pid][1]))  # dinero de ese ingrediente por plato
    rng = random.Random(77)
    n = 0
    inicio = HOY - timedelta(days=91)
    lunes = inicio - timedelta(days=inicio.weekday())
    while lunes < HOY:
        fin = lunes + timedelta(days=6)
        filas = conn.execute("SELECT receta_id, sum(producido) FROM Ventas WHERE fecha BETWEEN ? AND ? GROUP BY receta_id",
                             (lunes.isoformat(), fin.isoformat())).fetchall()
        monto = sum((costos.get(rid) or 0) * prod for rid, prod in filas) * rng.uniform(1.06, 1.14)
        peso: dict[int, float] = {}
        for rid, prod in filas:
            for pid, dinero_plato in usos.get(rid, []):
                peso[pid] = peso.get(pid, 0) + dinero_plato * prod
        total_peso = sum(peso.values())
        if monto > 0 and total_peso > 0:
            principales = sorted(peso.items(), key=lambda kv: -kv[1])[:18]
            suma_p = sum(v for _, v in principales)
            for dia in (lunes, lunes + timedelta(days=3)):  # lunes y jueves
                if dia >= HOY:
                    continue
                for pid, v in principales:
                    prov_id, precio, unidad = precios[pid]
                    gasto = monto / 2 * v / suma_p
                    cantidad = max(round(gasto / precio), 1) if unidad == "unidad" else max(round(gasto / precio, 1), 0.1)  # unidades enteras
                    conn.execute("INSERT INTO Compras (fecha, proveedor_id, producto_id, cantidad, unidad, precio, unidad_precio, total, es_demo) "
                                 "VALUES (?,?,?,?,?,?,?,?,1)",
                                 (dia.isoformat(), prov_id, pid, cantidad, unidad, precio, unidad, round(cantidad * precio, 2)))
                    n += 1
        lunes += timedelta(days=7)
    return {"filas": n}


def paso_conteos(conn: sqlite3.Connection) -> dict:
    """Conteos FICTICIOS cerrados a fin de cada mes con compras de demostracion. Por producto, lo que «queda en el almacen»
    son entre 3 y 6 dias de sus compras. No tocan el inventario real."""
    conn.execute("DELETE FROM ConteoLineas WHERE conteo_id IN (SELECT id FROM Conteos WHERE es_demo=1)")
    conn.execute("DELETE FROM Conteos WHERE es_demo=1")
    rango = conn.execute("SELECT min(fecha), max(fecha) FROM Compras WHERE es_demo=1").fetchone()
    if not rango[0]:
        return {"conteos": 0}
    ini, fin = date.fromisoformat(rango[0]), date.fromisoformat(rango[1])
    fechas = []
    m = date(ini.year, ini.month, 1)
    while True:
        siguiente = date(m.year + (m.month == 12), m.month % 12 + 1, 1)
        ultimo = siguiente - timedelta(days=1)
        if ultimo > fin:
            break
        if ultimo >= ini:
            fechas.append(ultimo)
        m = siguiente
    rng = random.Random(31)
    for f in fechas:
        desde = (f - timedelta(days=27)).isoformat()
        filas = conn.execute("SELECT producto_id, unidad_precio, sum(cantidad), avg(precio) FROM Compras WHERE es_demo=1 AND fecha BETWEEN ? AND ? "
                             "GROUP BY producto_id, unidad_precio", (desde, f.isoformat())).fetchall()
        cid = conn.execute("INSERT INTO Conteos (fecha, estado, cerrado_por, cerrado_en, es_demo, notas) VALUES (?, 'cerrado', 'Demostración', ?, 1, "
                           "'DATO FICTICIO de demostración')", (f.isoformat(), f"{f.isoformat()} 22:00:00")).lastrowid
        v_total = 0.0
        for pid, unidad, comprado_28, precio in filas:
            queda = round(comprado_28 / 28 * rng.uniform(3, 6), 1 if unidad != "unidad" else 0)
            sistema = round(queda * rng.uniform(1.0, 1.06), 1 if unidad != "unidad" else 0)  # el sistema suele creer que hay un poco mas
            conn.execute("INSERT INTO ConteoLineas (conteo_id, producto_id, unidad, cantidad_sistema, cantidad_contada, precio) VALUES (?,?,?,?,?,?)",
                         (cid, pid, unidad, sistema, queda, round(precio, 4)))
            v_total += queda * precio
        conn.execute("UPDATE Conteos SET valor_contado=?, valor_sistema=(SELECT round(sum(cantidad_sistema*precio),2) FROM ConteoLineas WHERE conteo_id=?) "
                     "WHERE id=?", (round(v_total, 2), cid, cid))
    return {"conteos": len(fechas)}


# Peso tipico de 1 unidad (kg). Es referencia comun de cocina, no un dato ficticio: solo se pone si el producto no tiene peso.
PESOS_TIPICOS = {
    "Huevo": 0.06, "Yemas": 0.018, "Yema": 0.018, "Yemas De Huevo": 0.018, "Plátano Verde": 0.3, "Banana Madura": 0.12,
    "Limon": 0.06, "Lima": 0.06, "Naranja": 0.2, "Naranjas Enteras": 0.2, "Mandarinas": 0.1, "Piña": 1.5, "Cebolla": 0.15,
    "Pepino": 0.3, "Manzana Verde": 0.18, "Zanahoria": 0.1, "Maracuyás": 0.09, "Hoja De Plátano": 0.05, "Arepa": 0.1,
    "Chile": 0.02, "Pato": 2.2, "Tostada De Maíz": 0.03, "Brevas Maduras": 0.05,
}
MOTIVOS_DEMO = ("Quemado", "Se cayó al piso", "Sobrante de preparación", "Mal porcionado")
TURNO_CON_FUGA = (HOY - timedelta(days=3), "vespertino")  # este turno pierde 7 % sin explicar (para ver la alarma)


def paso_balance(conn: sqlite3.Connection) -> dict:
    """Balance del turno FICTICIO de los ultimos 7 dias. Bodega entrega lo que piden las recetas vendidas, mas lo que luego
    se anota (merma pesada, comida del personal, residuo de limpieza), mas una fuga de 0 a 2 % (7 % en TURNO_CON_FUGA).
    Las entregas NO descuentan el inventario (desconto_inventario=0). Todo es es_demo=1."""
    from data import proveedores as prov
    from data.balance import a_kg
    from core.unidades import convertir, familia
    from core.normalizar import motivo_canonico
    from data.turnos import TURNOS
    for t in ("MovimientosTurno", "SalidasTurno", "Mermas"):
        conn.execute(f"DELETE FROM {t} WHERE es_demo=1")
    pesos = sum(conn.execute("UPDATE Catalogo SET kg_por_unidad=? WHERE nombre=? AND kg_por_unidad IS NULL", (kg, n)).rowcount
                for n, kg in PESOS_TIPICOS.items())
    # bases creadas antes de corregir paso_proveedores: precio FICTICIO «por unidad» que en realidad era por kg.
    # Solo si sale a mas de $25 el kg (absurdo para huevos o frutas); despues de corregir ya no pasa, asi que no se repite.
    precios_corregidos = 0
    for n, kg in PESOS_TIPICOS.items():
        precios_corregidos += conn.execute(
            "UPDATE ProveedorProductos SET precio=max(round(precio*?, 2), 0.01) WHERE es_demo=1 AND unidad_precio='unidad' "
            "AND precio/? > 25 AND producto_id=(SELECT id FROM Catalogo WHERE nombre=?)", (kg, kg, n)).rowcount
    kgu = {r[0]: r[1] for r in conn.execute("SELECT id, kg_por_unidad FROM Catalogo")}
    nombres = {r[0]: r[1] for r in conn.execute("SELECT id, nombre FROM Catalogo")}
    ings: dict[str, list] = {}
    liquido: set = set()
    for rid, pid, cant, uni in conn.execute("SELECT receta_id, producto_id, cantidad, unidad FROM RecetaIngredientes WHERE producto_id IS NOT NULL"):
        kg = a_kg(cant, uni, kgu.get(pid))
        if kg:
            ings.setdefault(rid, []).append((pid, kg))
            if familia(uni) == "l":
                liquido.add(pid)
    antes = conn.row_factory
    conn.row_factory = sqlite3.Row  # mejor_precio_por_producto lee las filas por nombre
    try:
        mejores = prov.mejor_precio_por_producto(conn)
    finally:
        conn.row_factory = antes
    rng = random.Random(55)
    turnos = movs = 0
    for n in range(7, 0, -1):
        d = HOY - timedelta(days=n)
        for turno, servicios in TURNOS.items():
            uso: dict[int, float] = {}
            for rid, producido, serv in conn.execute("SELECT receta_id, producido, servicio FROM Ventas WHERE fecha=?", (d.isoformat(),)):
                if clave(serv) in servicios:
                    for pid, kg in ings.get(rid, []):
                        uso[pid] = uso.get(pid, 0) + kg * producido
            if not uso:
                continue
            turnos += 1
            total = sum(uso.values())
            anotado = 0.0
            for tipo, lo, hi, nota in (("comida_personal", 0.6, 1.8, "Almuerzo del personal"), ("residuo_limpieza", 0.3, 1.2, "Lo que quedó en la batidora y las ollas")):
                kg = round(rng.uniform(lo, hi), 1)
                anotado += kg
                conn.execute("INSERT INTO SalidasTurno (fecha, turno, tipo, kg, nota, persona, es_demo) VALUES (?,?,?,?,?,?,1)",
                             (d.isoformat(), turno, tipo, kg, nota, "Chef de turno (demo)"))
            for pid in sorted(uso, key=lambda p: -uso[p])[:rng.randint(1, 2)]:
                kg = round(uso[pid] * rng.uniform(0.01, 0.03), 2)
                if kg <= 0:
                    continue
                anotado += kg
                m = mejores.get(pid)
                eq = convertir(kg, "kg", m["unidad_precio"]) if m else None
                conn.execute("INSERT INTO Mermas (fecha, producto, cantidad, unidad, motivo, costo_estimado, turno, es_demo) VALUES (?,?,?,?,?,?,?,1)",
                             (d.isoformat(), nombres[pid], kg, "kg", motivo_canonico(rng.choice(MOTIVOS_DEMO)),
                              round(eq * m["precio"], 2) if eq is not None else 0.0, turno))
            con_fuga = (d, turno) == TURNO_CON_FUGA
            fuga = 0.0 if con_fuga else rng.uniform(0.003, 0.015)
            mayor = max(uso, key=lambda p: uso[p])
            devolucion = round(rng.uniform(0.5, 2.0), 1) if rng.random() < 0.35 else 0.0  # a veces sobra y se devuelve a bodega
            for pid, kg in uso.items():
                entregar = kg * (1 + fuga) + anotado * kg / total + (devolucion if pid == mayor else 0)
                if con_fuga and pid == mayor:  # el 7 % que se pierde sale todo de un ingrediente: el balance debe señalarlo
                    entregar += total * 0.07
                unidad = "l" if pid in liquido else "kg"
                cant = round(entregar / (kgu.get(pid) or 1) if unidad == "l" else entregar, 2)
                if cant <= 0:
                    continue
                conn.execute("INSERT INTO MovimientosTurno (fecha, turno, tipo, producto_id, cantidad, unidad, entrego, recibio, desconto_inventario, es_demo) "
                             "VALUES (?,?,?,?,?,?,?,?,0,1)", (d.isoformat(), turno, "entrega", pid, cant, unidad, "Bodega (demo)", "Chef de turno (demo)"))
                movs += 1
            if devolucion:
                conn.execute("INSERT INTO MovimientosTurno (fecha, turno, tipo, producto_id, cantidad, unidad, entrego, recibio, desconto_inventario, es_demo) "
                             "VALUES (?,?,?,?,?,?,?,?,0,1)", (d.isoformat(), turno, "devolucion", mayor, devolucion, "kg", "Chef de turno (demo)", "Bodega (demo)"))
                movs += 1
    return {"turnos": turnos, "movimientos": movs, "pesos_por_unidad": pesos, "precios_corregidos": precios_corregidos}


PASOS = ("ingredientes", "proveedores", "ventas", "compras", "conteos", "balance")


def main(db_path: str | None = None, pasos: tuple = PASOS) -> dict:
    """pasos: cuales partes correr. OJO: «proveedores» borra y recrea los proveedores y precios de DEMOSTRACION
    (es_demo=1), asi que deshace los cambios que hayas hecho sobre ellos. Lo que creaste tu (es_demo=0) no se toca."""
    db = Path(db_path) if db_path else RAIZ / "chefchat.db"
    bak = db.with_suffix(".pre_etapa_b.bak")
    if not bak.exists():
        shutil.copy2(db, bak)
    asegurar_esquema(str(db))
    conn = sqlite3.connect(db)
    try:
        funciones = {"ingredientes": paso_ingredientes, "proveedores": paso_proveedores, "ventas": paso_ventas, "compras": paso_compras, "conteos": paso_conteos,
                     "balance": paso_balance}
        r = {p: funciones[p](conn) for p in PASOS if p in pasos}
        conn.commit()
        return r
    finally:
        conn.close()


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Datos de la etapa B (ficticios donde se indica).")
    ap.add_argument("--solo", choices=PASOS, action="append", help="correr solo esta parte (se puede repetir)")
    args = ap.parse_args()
    print(main(pasos=tuple(args.solo) if args.solo else PASOS))




