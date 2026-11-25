# Plan por etapas: ChefChat para el dueño del restaurante

Fecha: 25 nov 2026. Estado: Etapas A a F hechas, con registro de compras y costo real contra teórico, conteo de inventario al cierre de mes (costo real exacto) y balance del turno en kilos y unidades (`docs/PLAN_BALANCE_TURNO.md`).

## Qué pide el cliente (el dueño)
Controlar el negocio por dentro: inventario, mermas, capacitación, papeleo del personal, compras, menú y costos, y saber qué pasó en cada turno.

## Etapa A (hecha)
- Tarjeta "Costo de mermas" ya no se corta.
- Asistente en burbuja flotante, en todas las pantallas.
- Capacitación con 72 preguntas aprobadas (28 BPM, 20 Atención, 25 Alérgenos; 3 siguen pendientes).
- Pantalla **Manuales**: leer e imprimir.
- Foquito 💡 cuando queda 1 día o menos para vencer.

## Qué ya existe en la base (sirve de punto de partida)
| Dato | Cantidad | Nota |
|---|---|---|
| Recetas con ingredientes, costo y porciones | 280 filas (`RecetasRAG`) | Ingredientes en texto `cantidad\|unidad\|nombre` |
| Menú semanal con precio de venta | 32 (`MenuSemanalPro`) | Desayuno, almuerzo, cena |
| Producción diaria | 12 (`ProduccionDiaria`) | Faltan datos de ventas |
| Sobrantes reutilizables | 2 | Ya tiene "días de reutilización" |
| Ventas históricas | 0 | **Hay que crear datos de ejemplo** |
| Precios de compra por producto | no hay | **Hay que crearlos (proveedores)** |
| Productos de limpieza | 7 en `Limpieza` | Se mezclan con alimentos |

## Etapas propuestas (en este orden)

### B. Base de datos: lo que falta para todo lo demás (HECHA el 24 nov)
Script: `scripts/etapa_b_datos.py`. Pruebas: `tests/test_etapa_b.py`. Resultado: 2.048 líneas de ingredientes, 71 % ligadas a un producto; 6 proveedores y 627 precios ficticios; 386 ventas ficticias (90 días). Los ingredientes que quedan sin producto son agua, hielo y los poco usados.
Pendiente de B: la tabla `InformesTurno` está creada pero vacía (se llena en la etapa F).
1. `Catalogo.tipo` = `alimento` o `limpieza` (se deduce de la categoría y se puede corregir).
2. Tabla `Proveedores` (nombre, contacto, días de entrega, notas).
3. Tabla `ProveedorProductos` (proveedor, producto, precio, unidad, fecha del precio). Guarda el historial de precios.
4. Tabla `Ventas` (fecha, plato, cantidad, precio) con datos ficticios de 90 días.
5. Tabla `InformesTurno` (fecha, turno, chef, personal, producido, merma, merma recuperada, incidencias, observaciones).
6. Tabla `RecetaIngredientes` (receta, producto del catálogo, cantidad, unidad). Hoy los ingredientes son texto suelto: sin esto no se puede calcular costos bien.

### C. Pantallas de proveedores y de recetas
- **Proveedores**: lista, qué vende cada uno y a qué precio. Para cada producto: "el más barato es X". Alerta si un precio subió más de 10 %.
- **Recetas**: lista, ficha con ingredientes, costo por porción, margen contra el precio de venta, alérgenos. Imprimible.
- **Alimentos y limpieza** separados en Inventario con un filtro. La luz 💡 solo para alimentos.

### D. Menú y costos con el asistente
- Costo por persona de desayuno, almuerzo y merienda, usando precios de proveedores. Fórmula visible: costo del plato = suma(cantidad × precio del ingrediente) / porciones.
- El asistente propone un menú del día o de la semana con un tope de costo por persona y respeta alérgenos.
- "Qué cocinar con lo que vence mañana": cruza lotes que vencen en 24 h con recetas que los usan. Es consulta directa a la base. La IA solo redacta.
- "Cómo aprovechar la merma": sugiere recetas con sobrantes reutilizables dentro de su plazo sanitario.
- Regla de seguridad: el menú y los costos los calcula código, no la IA. La IA no inventa precios.

### E. Panel del dueño: análisis de datos
- Merma por mes, por motivo y por producto. Tendencia.
- Merma recuperada contra merma perdida (en dinero).
- Producido contra vendido por plato, y lo que sobra.
- Costo teórico contra costo real de alimentos (diferencia = fuga).
- Platos que más dejan: margen y ventas.
- Compras por proveedor.
- Resultados de capacitación por persona.
- Cada gráfico dice en una frase qué significa y qué hacer.

### F. Informe del turno para el gerente
- El chef llena un formulario corto: chef, personal del turno (desde `Trabajadores`), producido, merma, merma recuperada, incidencias, observaciones.
- Los números se llenan solos desde la base. El chef revisa y firma.
- Se ve en pantalla, se imprime y se guarda en historial. El gerente lo ve en el Panel.

## Otras mejoras recomendadas (investigado)
Fuentes: guías de software de cocina como [Operandio](https://operandio.com/best-kitchen-management-software/) y [MarginEdge/gitnux](https://gitnux.org/best/restaurant-back-office-software/). Resumen con mis palabras: el software de cocina se divide en control de costos (inventario, recetas, compras) y control de ejecución (listas de revisión, temperaturas, limpieza, capacitación). El dato más útil es comparar costo teórico y costo real.

| Mejora | Por qué sirve | Esfuerzo |
|---|---|---|
| Costo teórico contra real | Encuentra fugas de dinero | Medio (necesita Ventas y RecetaIngredientes) |
| Pedido sugerido de compra | "Compra 20 kg de pollo" según stock mínimo y consumo | Medio |
| Registro de temperaturas (neveras) | Exigido por buenas prácticas (BPM) | Bajo |
| Listas de apertura y cierre | Orden y limpieza firmados | Bajo |
| Alérgenos por plato en el menú | Seguridad del cliente | Bajo (ya hay dato en recetas) |
| Roles: dueño, chef, trabajador | Que el trabajador no vea costos | Medio |
| Respaldo automático de la base | No perder datos | Bajo |
| Registro de cambios (quién hizo qué) | Control y confianza | Medio |

## Reglas de calidad (en todas las etapas)
1. Primero los datos y su prueba, después la pantalla.
2. Cálculos de dinero y fechas: siempre código con pruebas, nunca la IA.
3. Cada etapa termina con pruebas que pasan y una revisión visual en el navegador.
4. Datos ficticios marcados como tales.
5. Cambios en la base: con copia de respaldo y repetibles.
