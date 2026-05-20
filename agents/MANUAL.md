# ChefChat Pro - Manual de Usuario

Sistema Operativo para Restaurantes - 35+ herramientas profesionales

---

## Índice

1. [Botones de la Interfaz](#1-botones-de-la-interfaz)
2. [Recetas](#2-recetas)
3. [Menú y Planificación](#3-menú-y-planificación)
4. [Inventario y Compras](#4-inventario-y-compras)
5. [Producción Diaria](#5-producción-diaria)
6. [Costos y Rentabilidad](#6-costos-y-rentabilidad)
7. [Mermas y Desperdicio](#7-mermas-y-desperdicio)
8. [Trabajadores y Sobrantes](#8-trabajadores-y-sobrantes)
9. [Dashboards Profesionales](#9-dashboards-profesionales)
10. [Office y Documentos](#10-office-y-documentos)
11. [Plantillas](#11-plantillas)
12. [Turnos de Cocina](#12-turnos-de-cocina)
13. [Incidencias](#13-incidencias)
14. [Prefijos de Recetas](#14-prefijos-de-recetas)
15. [Flujo de Trabajo Recomendado](#15-flujo-de-trabajo-recomendado)

---

## 1. Botones de la Interfaz

### Barra Lateral Izquierda

| Botón | Icono | Función |
|-------|-------|---------|
| **Chat** | 💬 | Muestra el panel principal de conversación con el asistente. Activo por defecto. |
| **Telemetría** | 📊 | Abre el dashboard de telemetría con gráficos de uso de IA: tokens, costos por modelo, gasto diario, total de peticiones. |
| **Configuración** | ⚙️ | Abre el diálogo de configuración de API Keys. Permite seleccionar proveedor (OpenRouter, Azure, Ollama, Gemini), ingresar API key y cambiar modelo. |
| **Tema** | 🌙/☀️ | Alterna entre tema oscuro y claro. Se aplica a toda la interfaz incluyendo paneles y diálogos. |

### Área de Chat (parte inferior)

| Botón | Icono/Texto | Función |
|-------|-------------|---------|
| **Enviar** | `Enviar` | Envía el mensaje escrito al asistente. También se puede presionar `Enter` en el campo de texto. |
| **Cargar Documentos** | 📂 `+` | Abre selector de archivos para cargar documentos CSV, MD o TXT al sistema RAG. Los documentos cargados se indexan y pueden ser consultados con comandos como "busca documento de higiene". |
| **Word** | 📄 `Word` | Envía la última respuesta visible a Microsoft Word. Si la respuesta contiene una receta, menú, reporte o lista, se formatea como documento. Requiere aprobación HITL. |
| **Excel** | 📊 `Excel` | Envía la última respuesta a Microsoft Excel. Si es una receta, envía tabla de ingredientes. Si es un dashboard exportado, abre el archivo .xlsx con gráficos. Requiere aprobación HITL. |
| **PowerPoint** | 📽️ `PPT` | Envía la última respuesta a Microsoft PowerPoint. Ideal para menús del día o presentaciones de recetas. Requiere aprobación HITL. |
| **Limpiar Chat** | 🧹 `Limpiar` | Borra todo el historial de conversación. No afecta la base de datos ni los datos del restaurante. |

### Barra de Aprobación HITL (aparece cuando es necesaria)

| Botón | Icono/Texto | Función |
|-------|-------------|---------|
| **Aprobar** | `✔ Aprobar` | Confirma y ejecuta la acción pendiente (enviar a Word, Excel, PowerPoint, aplicar plantilla, etc.). La barra se oculta y se muestra el resultado. |
| **Rechazar** | `✖ Rechazar` | Cancela la acción pendiente. Se muestra mensaje "Acción rechazada" en el chat. La barra se oculta. |

### Selector de Proveedor y Modelo (parte superior del chat)

| Elemento | Función |
|----------|---------|
| **Selector de Proveedor** | Dropdown para elegir proveedor de IA: OpenRouter, Azure OpenAI, Ollama, Gemini. Cambia el proveedor activo inmediatamente. |
| **Selector de Modelo** | Dropdown que muestra modelos disponibles según el proveedor seleccionado. Ej: OpenRouter muestra GPT-4o, GPT-4o-mini, Claude, etc. |
| **⚙️ (junto al selector)** | Atajo rápido para abrir configuración de API Keys. |

---

## 2. Recetas

Puedes buscar, escalar y planificar usando **lenguaje natural**.

### Buscar receta por ID
```
PLF-050
SOP-021
EVT-014
```

### Buscar receta por nombre
```
busca la receta Sopa de Calabacitas con Queso
dame la receta Arroz con Leche Andino
busca POS-011
```

### Escalar receta (multiplicar ingredientes)
```
PLF-050 para 112 personas
SOP-021 para 30 comensales
POS-004 para 50 pax
```
Escala todos los ingredientes proporcionalmente. Si el CSV tiene columna `Porciones` la usa como base; si no, asume 1 porción individual.

### Menú con ingredientes específicos
```
menú que tenga pollo, queso, arroz
un menú con cebolla, lechuga, cerdo, res, pollo
sugiere recetas con chocolate y fresa
```

### Buscar recetas que contengan un ingrediente
```
qué recetas llevan pollo
recetas con queso de cabra
```

---

## 3. Menú y Planificación

### Menú del día
```
menú del día
qué hay hoy en el menú
menu_diario
```

### Configurar menú semanal
```
configurar menú semanal Lunes | entrante=SOP-021, plato_fuerte=PLF-018, postre=POS-006
configurar_menu_semanal Martes | sopa=SOP-025, plato_fuerte=PLF-013
```

### Menú anti-desperdicio
```
sugiere menú con productos por caducar
menu_anti_desperdicio
```

### Planificar evento completo (menú + inventario + faltantes)
```
qué necesitamos para elaborar EVT-014; EVT-009; EVT-001
revisa inventario para EVT-011; EVT-015
que falta en bodega para PLF-050
planifica evento con SOP-021, PLF-018, POS-006 para 50 personas
```
Para múltiples recetas usa `;` como separador.

---

## 4. Inventario y Compras

### Revisar inventario para una o varias recetas
```
qué falta en bodega para hacer EVT-014
revisa inventario para PLF-050
que necesitamos comprar para EVT-011; EVT-015; EVT-001
```
El sistema calcula ingredientes totales, verifica stock y muestra **qué falta comprar**.

### Productos por caducar
```
qué productos están por caducar
productos_por_caducar 3
qué caduca en los próximos 7 días
```

### Stock bajo
```
qué productos tienen stock bajo
verificar_stock_bajo 10
alertas_stock_bajo
```

### Registrar uso de inventario
```
usé 2 kilos de pollo
registrar_uso_inventario Fresa, 2.5
```

### Lista de compras
```
genera lista de compras para SOP-021, PLF-018 para 50 personas
generar_lista_compras
```

### Órdenes de compra
```
generar orden de compra: Distribuidora ABC, pollo, 50, kg, 3.50
órdenes de compra pendientes
ordenes_compra recibida
```

---

## 5. Producción Diaria

### Registrar producción
```
registrar producción del día: SOP-021=30 raciones, PLF-018=20
registrar_produccion fecha=2025-06-15, cocido: SOP-021=30, sobrante: arroz=4.5|kg|no
```

### Dashboard de producción y ventas
```
dashboard de producción de los últimos 7 días
dashboard_ventas 30
```
Muestra producción cocida, sobrantes almacenados/desperdiciados, ingresos y ganancias.

### Generar reporte diario
```
generar reporte diario
generar_reporte_diario 2025-06-15
```

---

## 6. Costos y Rentabilidad

### Comparar costos reales vs teóricos
```
compara costos reales vs teóricos de los últimos 30 días
costo_real_vs_teorico 30
```
Compara el costo de producción real (basado en ventas registradas) vs el costo teórico de las recetas. Muestra margen de ganancia por receta.

### Analizar rentabilidad del menú
```
analizar rentabilidad del menú
qué recetas son las más rentables
analizar_rentabilidad
```
Clasifica recetas usando matriz BCG:
- **⭐ Estrellas**: Alta popularidad, alto margen
- **💰 Vacas**: Alta popularidad, bajo margen
- **❓ Interrogantes**: Baja popularidad, alto margen
- **🐕 Perros**: Baja popularidad, bajo margen

### Dashboard de ventas
```
dashboard de ventas
dashboard_ventas 7
```
Resumen económico con:
- Total de unidades vendidas
- Ingresos totales ($)
- Costos totales ($)
- Ganancia neta ($)
- Margen de ganancia (%)
- Desglose por día y receta

---

## 7. Mermas y Desperdicio

### Registrar merma
```
registrar merma: pollo, 2 kg, se contaminó, $5.50
registrar_merma cebolla, 1.5, kg, se echó a perder
```
Formato: `producto, cantidad, unidad, motivo, costo_estimado(opcional)`

### Reporte de mermas
```
reporte de mermas de la última semana
reporte_mermas 30
```
Muestra total de mermas, costo total, y desglose por producto y motivo.

---

## 8. Trabajadores y Sobrantes

### Registrar trabajador
```
registra al empleado EMP001, Juan Perez, Cocinero, matutino, 08:00, 16:00, Sabado-Domingo, activo, fijo
registrar_trabajador EMP002, Maria Lopez, Repostera, vespertino, 14:00, 22:00, Lunes-Martes, reposo, temporal
```
Turnos: matutino, vespertino, nocturno, mixto.
Estado: activo, reposo.
Tipo contrato: fijo, temporal.

### Listar trabajadores
```
lista de trabajadores del turno matutino
listar_trabajadores
qué empleados están registrados
lista trabajadores vespertino
```

### Registrar sobrante reutilizable
```
registra sobrante: arroz cocido, 4.5 kg, EMP001, matutino, 2 días
registrar_sobrante pollo guisado, 3.0, kg, EMP002, vespertino, 1
```
- `producto`: nombre del producto que sobró
- `cantidad`: lo que sobró
- `unidad`: kg, litros, piezas, etc.
- `id_empleado` (opcional): quién registró
- `turno` (opcional): matutino/vespertino/nocturno
- `dias_reutilizacion` (opcional, default 1): días sanitarios para reutilizar

### Dashboard de sobrantes
```
dashboard de sobrantes de los últimos 7 días
dashboard_sobrantes 30
qué sobrantes hay registrados
```
Muestra sobrantes por turno y día, destino (almacenado/reutilizado/desperdicio/donación), y top productos.

---

## 9. Dashboards Profesionales

Todos los dashboards generan archivos Excel (.xlsx) con **gráficos incrustados** que se abren automáticamente.

### Dashboard de Sobrantes
```
exporta dashboard de sobrantes a Excel
exportar_dashboard_sobrantes 7
```
Genera libro con **2 hojas** y **4 gráficos**:

**Hoja «Datos»** — Registros detallados con turno, producto, cantidad, destino, empleado.

**Hoja «Dashboard»** — Panel visual con:
- **KPIs**: Total kilos, registros, desperdicio, reutilizados
- **Gráfico 1 — Desperdicio por día**: barras de kilos desperdiciados por fecha
- **Gráfico 2 — Distribución por destino**: pastel con almacenado/reutilizado/desperdicio/donación
- **Gráfico 3 — Top productos sobrantes**: barras con los productos que más sobran
- **Gráfico 4 — Días con mayor desperdicio**: Top 5 días críticos

### Dashboard de Mermas
```
exporta dashboard de mermas a Excel
exportar_dashboard_mermas 7
exportar_dashboard_mermas 30
```
Genera libro con **2 hojas** y **4 gráficos**:

**Hoja «Datos»** — Registro detallado de mermas con fecha, producto, cantidad, unidad, motivo y costo estimado.

**Hoja «Dashboard»** — Panel visual con:
- **KPIs**: Total mermas, costo total, promedio/día, peor producto
- **Gráfico 1 — Mermas por día**: barras de cantidad desperdiciada por fecha
- **Gráfico 2 — Mermas por producto**: pastel con top 10 productos más afectados
- **Gráfico 3 — Mermas por motivo**: barras agrupadas por causa (contaminación, caducidad, etc.)
- **Gráfico 4 — Costo por día**: barras del costo económico diario de mermas

### Dashboard de Personal
```
exporta dashboard de personal a Excel
exportar_dashboard_personal
```
Genera libro con **2 hojas** y **5 gráficos**:

**Hoja «Datos»** — Lista completa de trabajadores con ID, nombre, cargo, turno, horarios, días de descanso, estado y tipo de contrato.

**Hoja «Dashboard»** — Panel visual con:
- **KPIs**: Total empleados, activos, en reposo, temporales
- **Gráfico 1 — Empleados por turno**: pastel con distribución matutino/vespertino/nocturno/mixto
- **Gráfico 2 — Empleados por cargo**: barras con cantidad por puesto
- **Gráfico 3 — Distribución por turno**: barras detalladas
- **Gráfico 4 — Activo vs Reposo**: pastel con estado del personal
- **Gráfico 5 — Fijo vs Temporal**: pastel con tipo de contrato

> Si Excel no está disponible, los dashboards generan archivos CSV alternativos.

---

## 10. Office y Documentos

Los botones **Word**, **Excel** y **PowerPoint** en la interfaz envían el contenido actual al programa de Office correspondiente.

### Enviar receta a Word
```
envía SOP-021 a Word
pasa PLF-050 a Word
```
O haz clic en el botón **📄 Word** después de buscar una receta.

### Enviar receta a Excel (como tabla de ingredientes)
```
envía POS-004 a Excel
```
O haz clic en el botón **📊 Excel**.

### Enviar menú a PowerPoint
```
envía SOP-021, PLF-018, POS-006 a PowerPoint
```
O haz clic en el botón **🖥️ PPT**.

### Enviar plan de inventario a Office
Cuando el sistema muestra un plan de inventario (con recetas, ingredientes y faltantes), los botones **Word/Excel** envían el **plan completo**, no solo una receta.

### Abrir dashboard exportado en Excel
Cuando exportas un dashboard profesional, el botón **📊 Excel** detecta automáticamente el archivo generado y lo abre con todos los gráficos incrustados.

**Requisitos:** Tener Microsoft Office instalado. Word/Excel/PowerPoint se abren automáticamente si no están abiertos.

---

## 11. Plantillas

### Listar plantillas disponibles
```
qué plantillas hay disponibles
listar_plantillas
```

### Usar plantilla con datos
```
usa la plantilla invitacion.docx con nombre=Juan, fecha=15 Junio
usar_plantilla reporte.docx | cliente=Maria, total=$1,500
```

**Cómo crear una plantilla:**
1. Diseña el documento en Word/PPT con el formato deseado
2. Donde quieras datos variables, escribe `{{nombre}}`, `{{fecha}}`, `{{lugar}}`, etc.
3. Guarda el archivo en la carpeta `plantillas/` del proyecto
4. Ejecuta `usar_plantilla` con los valores correspondientes

---

## 12. Turnos de Cocina

### Asignar turno
```
asigna turno para Juan Perez el 2025-06-15 en platos_fuertes de 08:00 a 16:00
asignar_turnos 2025-06-15, Juan Perez, platos_fuertes, 08:00, 16:00, SOP-021
```
Estaciones: entradas, sopas, platos_fuertes, postres, plancha, parrilla, vegetales, limpieza.

### Ver turnos
```
qué turnos hay hoy
ver turnos para 2025-06-15
ver_turnos
```

---

## 13. Incidencias

### Registrar incidencia
```
reporto que faltó leche para la producción
registrar_incidencia Inventario, Falta leche
registrar_incidencia Equipo, Horno no enciende
```

---

## 14. Prefijos de Recetas

| Prefijo | Categoría | Ejemplo |
|---------|-----------|---------|
| ENT | Entrantes | ENT-001 Empanadas de Queso |
| SOP | Sopas (serie 016-050) | SOP-021 Sopa de Yuca con Queso |
| SPO | Sopas (serie 001-050) | SPO-036 Sopa de Calabacitas con Queso |
| ENS | Ensaladas y Guarniciones | ENS-005 Choclo con Queso |
| PLF | Platos Fuertes | PLF-050 Cordero Patagónico |
| POS | Postres | POS-011 Empanadas Dulces |
| BEB | Bebidas | BEB-001 Horchata de Arroz |
| EVT | Eventos Especiales | EVT-014 Tartaletas de Queso Azul |
| REC | Recetas principales | REC-001 Pato a la Naranja |

> **Nota:** Para consultar varias recetas a la vez usa `;` como separador: `EVT-014; EVT-009; EVT-001`

---

## 15. Flujo de Trabajo Recomendado

### Diario
1. `menú del día` → ver el menú
2. *Botón [+] para cargar documentos* → ingestar documentos nuevos
3. `registrar producción del día` → registrar lo cocinado y sobrantes
4. `qué falta en bodega para PLF-050` → verificar inventario para recetas del día

### Semanal
1. `configurar menú semanal` → planificar la semana
2. `dashboard de producción 7` → revisar producción de la semana
3. `qué productos están por caducar 5` → revisar caducidades
4. `qué productos tienen stock bajo 20` → revisar stock crítico
5. `generar orden de compra` → ordenar lo que falta
6. *Botón Word* → enviar reportes a Office

### Mensual
1. `reporte de mermas 30` → revisar desperdicio del mes
2. `exportar_dashboard_mermas 30` → dashboard visual de mermas con gráficos
3. `compara costos reales vs teóricos 30` → revisar costos
4. `analizar rentabilidad del menú` → analizar rentabilidad
5. `exportar_dashboard_personal` → dashboard de personal con estado y contratos
6. `asignar turnos` → planificar turnos del mes
