# ChefChat Pro - Diccionario / Glosario

Terminología técnica, culinaria y de negocio utilizada en el sistema.

---

## A

| Término | Definición |
|---------|-----------|
| **Activo** | Estado de un trabajador que se encuentra laborando normalmente. |
| **AccionOffice** | Modelo Pydantic que define una operación de exportación a Word, Excel o PowerPoint. |
| **Agente** | Componente de IA especializado en una tarea (Recetas, Inventario, Menú, Mermas, Documentos). |
| **Almacenado** | Destino de un sobrante reutilizable que se guarda para uso posterior. |
| **Análisis BCG** | Matriz de rentabilidad que clasifica recetas en Estrellas, Vacas, Interrogantes y Perros. |

## B

| Término | Definición |
|---------|-----------|
| **BCG** | Boston Consulting Group. Matriz que cruza popularidad vs margen de ganancia. |
| **Bitácora** | Registro diario de operaciones de producción y eventos del restaurante. |
| **Botón Office** | Botones en la GUI (📄 Word, 📊 Excel, 🖥️ PPT) para exportar contenido a Microsoft Office. |

## C

| Término | Definición |
|---------|-----------|
| **Catalogo** | Tabla de productos base con nombre, categoría y vida útil en días. |
| **Caducidad** | Fecha en que un producto del inventario vence. Calculada como `fecha_ingreso + vida_util_dias`. |
| **Cargo** | Puesto de un trabajador (Cocinero, Repostero, Ayudante, etc.). |
| **Comensales** | Número de personas para las que se escala una receta. |
| **Costo de Producción** | Costo total de los ingredientes necesarios para preparar una receta. |
| **Costo Real** | Costo calculado a partir de ventas registradas, puede diferir del teórico. |
| **Costo Teórico** | Costo calculado a partir de la receta base en el sistema. |
| **Costo Unitario** | Precio por unidad de un producto en una orden de compra. |

## D

| Término | Definición |
|---------|-----------|
| **Dashboard** | Panel visual con gráficos y KPIs exportado a Excel. |
| **Días de Descanso** | Días de la semana en que un trabajador no labora (ej: Sábado-Domingo). |
| **Días Reutilización** | Días sanitarios durante los cuales un sobrante puede reutilizarse de forma segura. |
| **Donación** | Destino de un sobrante que se entrega a una organización benéfica. |
| **DSPy** | Framework de optimización de prompts con few-shot examples y feedback. |

## E

| Término | Definición |
|---------|-----------|
| **Escalar Receta** | Multiplicar proporcionalmente los ingredientes de una receta para N comensales. |
| **Estado (trabajador)** | Situación laboral: `activo` (laborando) o `reposo` (ausente temporalmente). |
| **Estrella (BCG)** | Receta con alta popularidad y alto margen de ganancia. |
| **Evento (EVT)** | Receta especial para ocasiones específicas (bodas, banquetes, celebraciones). |

## F

| Término | Definición |
|---------|-----------|
| **FAISS** | Facebook AI Similarity Search. Biblioteca para búsqueda de vectores semánticos. |
| **Fijo** | Tipo de contrato de trabajador permanente. |
| **Fecha de Caducidad** | Límite de consumo seguro de un producto. |
| **Fecha de Ingreso** | Fecha en que un producto entró al inventario. |
| **Fecha de Venta** | Fecha en que se registró una venta de producto terminado. |

## G

| Término | Definición |
|---------|-----------|
| **Ganancia Neta** | Diferencia entre ingresos totales y costos totales. |
| **Guardrails** | Sistema de protección contra inyección de prompts con 23+ patrones de detección. |
| **Guarnición** | Acompañamiento de un plato fuerte (ensaladas, arroz, papas, etc.). |

## H

| Término | Definición |
|---------|-----------|
| **HITL** | Human-in-the-Loop. Aprobación humana obligatoria para acciones críticas. |

## I

| Término | Definición |
|---------|-----------|
| **Incidencia** | Registro de un problema o evento anormal (falta de insumos, falla de equipo). |
| **Ingreso Total** | Suma de todos los `precio_venta × unidades_vendidas`. |
| **Inventario** | Stock actual de productos con cantidades, unidades y fechas. |
| **Interrogante (BCG)** | Receta con baja popularidad pero alto margen. Requiere más promoción. |

## K

| Término | Definición |
|---------|-----------|
| **KPI** | Key Performance Indicator. Métrica clave de rendimiento. |

## L

| Término | Definición |
|---------|-----------|
| **LangChain** | Framework para construir aplicaciones con LLMs y herramientas. |
| **Life Cycle** | Ciclo de vida de un producto desde ingreso hasta caducidad. |

## M

| Término | Definición |
|---------|-----------|
| **Margen de Ganancia** | Porcentaje `(precio_venta - costo_produccion) / precio_venta × 100`. |
| **MCP** | Model Context Protocol. Protocolo para integración con herramientas externas. |
| **Merma** | Producto desperdiciado por contaminación, caducidad u otra causa. |
| **MenuSemanal** | Planificación de platos para cada día y servicio de la semana. |
| **Mixto** | Turno que combina horarios (ej: mañana y tarde con interrupción). |

## N

| Término | Definición |
|---------|-----------|
| **Nocturno** | Turno de trabajo durante la noche (ej: 22:00 - 06:00). |

## O

| Término | Definición |
|---------|-----------|
| **OpenRouter** | Proveedor de IA que agrega múltiples modelos (GPT, Claude, Gemini, DeepSeek). |
| **Orden de Compra** | Solicitud formal de productos a un proveedor con cantidades y costos. |
| **Orchestrator** | Componente central que clasifica intenciones y rutea a la herramienta correcta. |

## P

| Término | Definición |
|---------|-----------|
| **Pax** | Abreviatura de "personas" usada para comensales. |
| **Perro (BCG)** | Receta con baja popularidad y bajo margen. Candidata a eliminar. |
| **Perecedero** | Producto que se descompone rápidamente y requiere refrigeración. |
| **Plantilla** | Documento Word/PPT con placeholders `{{variable}}` para generación automática. |
| **Precio de Venta** | Precio al que se vende una porción de receta al cliente final. |
| **Producción** | Registro de lo cocinado en un día (cocido) y sobrantes generados. |
| **Prompt** | Instrucción de texto enviada al modelo de IA. |
| **Pydantic** | Biblioteca de validación de datos con type hints. |
| **PyQt6** | Framework de interfaz gráfica para Python. |

## R

| Término | Definición |
|---------|-----------|
| **RAG** | Retrieval-Augmented Generation. Búsqueda de documentos para enriquecer respuestas. |
| **Rate Limiting** | Control de frecuencia de peticiones para evitar uso excesivo. |
| **Receta** | Instrucciones de preparación con ingredientes, cantidades y pasos. |
| **RecetasRAG** | Tabla de recetas almacenadas con ID, nombre, ingredientes y costos. |
| **Reposo** | Estado de un trabajador ausente temporalmente (enfermedad, vacaciones, etc.). |
| **Rentabilidad** | Capacidad de una receta para generar ganancia sobre su costo. |
| **Reutilizado** | Destino de un sobrante que se aprovechó en otra preparación. |

## S

| Término | Definición |
|---------|-----------|
| **Sandbox** | Directorio restringido para operaciones seguras de archivos. |
| **Servicio** | Momento de comida: desayuno, almuerzo, merienda, cena. |
| **Sobrante** | Producto que sobró después de la producción y puede reutilizarse. |
| **SobrantesReutilizables** | Tabla de sobrantes con producto, cantidad, turno, destino y días de reutilización. |
| **Stock Bajo** | Productos con cantidad por debajo del umbral configurable. |

## T

| Término | Definición |
|---------|-----------|
| **Telemetría** | Registro de uso del sistema: modelo, tokens, costo, duración, operación. |
| **Temporal** | Tipo de contrato de trabajador por tiempo limitado. |
| **Token** | Unidad de texto procesada por el modelo de IA. |
| **Turno** | Período de trabajo: matutino (mañana), vespertino (tarde), nocturno (noche), mixto. |
| **TurnosCocina** | Tabla de asignación de cocineros a estaciones por fecha. |

## V

| Término | Definición |
|---------|-----------|
| **Vaca (BCG)** | Receta con alta popularidad pero bajo margen. Genera flujo constante. |
| **Vida Útil** | Número máximo de días que un producto es seguro para consumo. |
| **Vista_Caducidad** | Vista SQL que calcula días restantes para cada producto del inventario. |

---

## Prefijos de Recetas

| Prefijo | Categoría | Rango | Ejemplo |
|---------|-----------|-------|---------|
| **ENT** | Entrantes | 001-050 | ENT-001 Empanadas de Queso |
| **SOP** | Sopas (serie alta) | 016-050 | SOP-021 Sopa de Yuca con Queso |
| **SPO** | Sopas (serie baja) | 001-050 | SPO-036 Sopa de Calabacitas con Queso |
| **ENS** | Ensaladas y Guarniciones | 001-050 | ENS-005 Choclo con Queso |
| **PLF** | Platos Fuertes | 001-050 | PLF-050 Cordero Patagónico |
| **POS** | Postres | 001-050 | POS-011 Empanadas Dulces |
| **BEB** | Bebidas | 001-050 | BEB-001 Horchata de Arroz |
| **EVT** | Eventos Especiales | 001-050 | EVT-014 Tartaletas de Queso Azul |
| **REC** | Recetas Principales | 001-999 | REC-001 Pato a la Naranja |

---

## Tablas de la Base de Datos

| Tabla | Descripción |
|-------|-------------|
| `Catalogo` | Catálogo de productos con nombre, categoría y vida útil |
| `Inventario` | Stock actual con fecha_ingreso, cantidad, unidad |
| `RecetasRAG` | Recetas con ingredientes, comensales, costo_produccion |
| `Mermas` | Desperdicios con producto, cantidad, motivo, costo_estimado |
| `Trabajadores` | Personal con cargo, turno, estado, tipo_contrato |
| `SobrantesReutilizables` | Sobrantes con producto, cantidad, turno, destino |
| `OrdenesCompra` | Órdenes con proveedor, producto, costo_unitario, estado |
| `MenuSemanal` | Planificación semanal con dia_semana, tipo_comida, receta_id |
| `TurnosCocina` | Asignación de cocineros a estaciones por fecha |
| `Incidencias` | Bitácora de problemas con categoria, descripcion |
| `Ventas` | Registro de ventas con unidades, precio_venta, costo_produccion |
| `Produccion` | Producción diaria con tipo (cocido/sobrante), producto, cantidad |
| `Telemetria` | Métricas de IA con modelo, tokens, costo_total_usd |
| `DocumentosRAG` | Documentos cargados con tipo, nombre, estado |
| `DocumentosTexto` | Contenido de texto de documentos RAG |
| `BitacoraDiaria` | Registro diario de operaciones |
| `Recetas` | Recetas legacy con nombre, ingredientes, costo_produccion |

---

## Modelos Pydantic

| Modelo | Descripción |
|--------|-------------|
| `AccionOffice` | Define operación de exportación: herramienta, operacion, payload, requiere_hitl |
| `Configuracion` | Configuración del proveedor de IA: provider, model, api_key, endpoint |

---

## Agentes del Sistema

| Agente | Responsabilidad |
|--------|----------------|
| **Orchestrator** | Clasifica intención, detecta prioridad, rutea a herramienta o LLM |
| **Planner** | Analiza peticiones complejas y descompone en tareas |
| **Executor** | Ejecuta tareas del Planner y combina resultados |
| **Recipe Agent** | Búsqueda, escalado y sugerencia de recetas |
| **Inventory Agent** | Caducidad, stock bajo, órdenes de compra |
| **Menu Agent** | Planificación semanal, eventos, menú anti-desperdicio |
| **Waste Agent** | Registro y reporte de mermas |
| **Document Agent** | Búsqueda RAG de documentos de capacitación |

---

## Proveedor de IA

| Proveedor | Descripción |
|-----------|-------------|
| **OpenRouter** | API que agrega múltiples modelos (GPT-4o, Claude, Gemini, DeepSeek) |
| **Azure OpenAI** | Servicio enterprise de Microsoft para modelos OpenAI |
| **Ollama** | Ejecución local de modelos open-source (gratuito) |
| **DeepSeek** | Modelo de IA de código abierto, disponible vía OpenRouter |

---

## Estados y Destinos

### Estados de Trabajadores
| Estado | Significado |
|--------|-------------|
| `activo` | Trabajando normalmente |
| `reposo` | Ausente temporalmente (enfermedad, vacaciones, permiso) |

### Tipos de Contrato
| Tipo | Significado |
|------|-------------|
| `fijo` | Contrato permanente |
| `temporal` | Contrato por tiempo limitado |

### Destinos de Sobrantes
| Destino | Significado |
|---------|-------------|
| `almacenado` | Guardado para uso posterior |
| `reutilizado` | Aprovechado en otra preparación |
| `desperdicio` | Desechado |
| `donacion` | Entregado a organización benéfica |

### Estados de Órdenes de Compra
| Estado | Significado |
|--------|-------------|
| `pendiente` | Orden creada, esperando entrega |
| `recibida` | Producto recibido en bodega |
| `cancelada` | Orden cancelada |

---

## Herramientas LangChain (35+)

| Herramienta | Descripción |
|-------------|-------------|
| `buscar_receta` | Busca receta por nombre o ID |
| `escalar_receta` | Escala receta para N comensales |
| `sugerir_recetas_con_ingrediente` | Busca recetas que contengan un ingrediente |
| `sugerir_menu_por_ingredientes` | Sugiere menú completo basado en ingredientes |
| `consultar_menu_semanal` | Consulta el menú semanal |
| `configurar_menu_semanal` | Configura el menú de la semana |
| `agregar_plato_menu` | Agrega plato al menú semanal |
| `agregar_receta_al_menu` | Agrega receta RAG al menú |
| `modificar_plato_menu` | Modifica plato del menú |
| `eliminar_plato_menu` | Elimina plato del menú |
| `reset_menu_semanal` | Resetea todo el menú semanal |
| `menu_anti_desperdicio` | Sugiere menú con productos por caducar |
| `generar_lista_compras` | Genera lista de compras para recetas |
| `productos_por_caducar` | Lista productos próximos a caducar |
| `verificar_stock_bajo` | Lista productos con stock bajo |
| `alertas_stock_bajo` | Alertas de inventario bajo |
| `registrar_uso_inventario` | Registra uso de producto del inventario |
| `generar_orden_compra` | Crea orden de compra |
| `ordenes_compra` | Lista órdenes de compra |
| `actualizar_estado_orden` | Actualiza estado de orden |
| `registrar_merma` | Registra merma/desperdicio |
| `reporte_mermas` | Reporte de mermas del período |
| `exportar_dashboard_mermas` | Dashboard Excel de mermas con gráficos |
| `registrar_trabajador` | Registra trabajador |
| `listar_trabajadores` | Lista trabajadores por turno |
| `registrar_sobrante` | Registra sobrante reutilizable |
| `dashboard_sobrantes` | Dashboard de sobrantes |
| `exportar_dashboard_sobrantes` | Dashboard Excel de sobrantes con gráficos |
| `exportar_dashboard_personal` | Dashboard Excel de personal con gráficos |
| `registrar_produccion` | Registra producción diaria |
| `dashboard_ventas` | Dashboard de producción y ventas |
| `generar_reporte_diario` | Genera reporte diario oficial |
| `costo_real_vs_teorico` | Compara costos reales vs teóricos |
| `analizar_rentabilidad` | Analiza rentabilidad del menú (BCG) |
| `asignar_turnos` | Asigna turnos de cocina |
| `ver_turnos` | Ver turnos de cocina |
| `registrar_incidencia` | Registra incidencia |
| `registrar_venta` | Registra venta de producto |
| `buscar_documento` | Busca documento RAG |
| `listar_plantillas` | Lista plantillas disponibles |
| `usar_plantilla` | Usa plantilla con datos |
| `enviar_receta_a_word` | Envía receta a Word |
| `enviar_receta_a_excel` | Envía receta a Excel |
| `enviar_menu_a_powerpoint` | Envía menú a PowerPoint |
