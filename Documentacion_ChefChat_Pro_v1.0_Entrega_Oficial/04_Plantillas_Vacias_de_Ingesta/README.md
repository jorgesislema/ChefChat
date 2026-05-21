# Plantillas Vacias de Ingesta

Esta carpeta contiene las plantillas de datos que el cliente final debe completar para poblar el sistema ChefChat Pro.

## Instrucciones de Uso

1. Completar cada archivo CSV con los datos del restaurante
2. Colocar los archivos en `data_source/` del proyecto
3. Ejecutar `python scripts/data_seeder.py` para importar los datos
4. Verificar con consultas en el chat

## Archivos de Plantilla

| Archivo | Descripcion | Columnas Requeridas |
|---------|-------------|---------------------|
| `catalogo_productos.csv` | Catalogo de productos del restaurante | nombre, categoria, vida_util_dias |
| `inventario_inicial.csv` | Stock inicial de inventario | producto_id, lote, cantidad, unidad, fecha_ingreso, fecha_caducidad |
| `recetario.csv` | Recetas del restaurante | nombre, ingredientes, comensales, costo_produccion |
| `personal.csv` | Empleados del restaurante | id_empleado, nombre, cargo, turno, hora_entrada, hora_salida |
| `menu_semanal.csv` | Menu semanal base | dia_semana, tipo_comida, nombre_plato, precio_venta |

## Formato de Archivos

- Formato: CSV (UTF-8)
- Delimitador: coma (,)
- Texto entre comillas dobles (")
- Decimales con punto (.)
- Fechas en formato ISO (YYYY-MM-DD)

## Notas Importantes

- No modificar los nombres de las columnas
- Los archivos son procesados automaticamente por el clasificador RAG
- Los datos duplicados son detectados y rechazados
- Para recetas, usar formato JSON en la columna `ingredientes`

---

*Documento generado para ChefChat Pro v1.0 — Mayo 2026*
