# ChefChat Pro - Resumen del Proyecto

## 1. Vision General

ChefChat Pro es un asistente de escritorio para gestion de restaurantes que combina IA conversacional, agentes especializados con prompts individuales, RAG (Retrieval-Augmented Generation) e integracion con Microsoft Office. Construido con PyQt6 para Windows, utiliza un sistema multiagente donde cada agente tiene su propio prompt de sistema y usa el LLM seleccionado por el usuario.

## 2. Estructura del Repositorio

```
ChefChat/
├── main.py                    # Punto de entrada de la aplicacion
├── documentacion.py           # Generador de documentacion Word + HTML
├── requirements.txt           # Dependencias Python
├── chefchat.db                # Base de datos SQLite (17+ tablas)
├── pyrightconfig.json         # Configuracion de type checking
├── .gitignore                 # Archivos excluidos de git
│
├── agents/                    # Agentes de IA y orquestacion
│   ├── orchestrator.py        # Orquestador principal con routing y alertas
│   ├── multiagent.py          # Sistema multiagente (5 agentes + Planner + Executor)
│   ├── tools.py               # 58 herramientas operativas
│   ├── alertas.py             # Sistema de alertas cruzadas entre agentes
│   └── mcp_client.py          # Cliente MCP para Office
│
├── core/                      # Componentes centrales
│   ├── config.py              # Configuracion y 7 proveedores AI
│   ├── models.py              # Modelos Pydantic y contratos
│   ├── security.py            # Validacion de seguridad
│   └── rag_classifier.py      # Clasificador automatico de documentos
│
├── data/                      # Gestion de datos y RAG
│   ├── db_manager.py          # Gestor SQLite con seed_mermas y personal
│   ├── rag_store.py           # Almacen RAG con deteccion de duplicados
│   └── menu_semanal.py        # CRUD MenuSemanalPro con RAG
│
├── data_source/               # Fuentes de datos externas
│   ├── 1_recetas/             # 18 archivos CSV de recetas
│   └── 3_inventario/          # Catalogo y lotes de inventario
│
├── evaluation/                # Evaluaciones y metricas
│   └── [archivos de evaluacion]
│
├── gui/                       # Interfaz grafica PyQt6
│   ├── main_window.py         # Ventana principal con sidebar
│   ├── worker.py              # Worker thread con HITL
│   └── telemetry_view.py      # Dashboard de telemetria
│
├── ops/                       # Operaciones y seguridad
│   └── guardrails.py          # Proteccion contra inyeccion de prompts
│
├── prompting/                 # Optimizacion de prompts
│   └── dspy_optimizer.py      # Optimizador estilo DSPy
│
├── scripts/                   # Scripts de utilidad
│   ├── data_seeder.py         # Poblacion inicial de datos
│   └── [scripts de diagnostico]
│
├── tests/                     # 38 tests unitarios e integracion
│   └── [archivos de prueba]
│
├── plantillas/                # Plantillas Office
├── imagenes/                  # Recursos graficos
├── telemetry_exports/         # Exportaciones de telemetria
│
└── docs_internos/             # Documentacion interna
    ├── resumen.md             # ESTE ARCHIVO
    ├── architecture.md        # Arquitectura conceptual
    └── [17 documentos]
```

## 3. Arquitectura del Sistema

### 3.1 Patron Principal
- **Clean Architecture + MVC + Multiagente con LLM compartido**
- Separacion estricta entre GUI (PyQt6), logica de negocio (Pydantic) e infraestructura

### 3.2 Componentes Clave

| Componente | Responsabilidad | Tecnologia |
|------------|----------------|-------------|
| Orchestrator | Routing con 9 prioridades + alertas cruzadas | LangChain + regex |
| Multiagent System | 5 agentes con prompts individuales + LLM | ABC + LangChain |
| AlertManager | Alertas proactivas entre agentes (1er mensaje) | SQLite + heuristicas |
| Guardrails | Proteccion contra inyeccion de prompts | 23 patrones |
| RAG Engine | Busqueda semantica en documentos | SQLite LIKE + full text |
| MCP Client | Integracion con Word/Excel/PowerPoint | COM automation |
| HITL Controller | Aprobacion humana antes de acciones criticas | threading.Event + Qt |
| Telemetry | Registro de metricas y rendimiento | SQLite + CSV/JSON |

### 3.3 Proveedores de IA

| Proveedor | Modelo | Costo |
|-----------|--------|-------|
| DeepSeek | deepseek-chat | Bajo |
| OpenRouter | MiniMax 2.7b | Bajo |
| Ollama | llama3.2, mistral | Gratis |
| OpenAI | gpt-4o | Medio |
| Claude | claude-3-5-sonnet | Medio |
| Gemini | gemini-1.5-flash | Bajo |
| OpenCode | big-pickle | Gratis |

## 4. Flujo de Procesamiento

### 4.1 Flujo Principal de Peticion

```
1. Usuario envia peticion en GUI (selecciona agente o modo Auto)
2. Guardrails valida la entrada
3. Orchestrator clasifica por prioridad (9 niveles):
   PRI 1: Exportacion a Word/Excel/PPT
   PRI 2: Menu semanal
   PRI 3: Busqueda de documentos (RAG)
   PRI 3.5: Consultas de personal
   PRI 4: Receta por ID
   PRI 5: Menu por ingredientes
   PRI 6: Mermas con extraccion de fecha
   PRI 7: Receta por nombre
   PRI 8: Herramientas detectables
   PRI 9: LLM directo (fallback)
4. Si agente forzado: ruteo directo al agente con su prompt
5. AlertManager inyecta alertas cruzadas (solo 1er mensaje)
6. Contexto de exportacion guardado automaticamente
7. Respuesta enviada a GUI
```

### 4.2 Sistema Multiagente (v2.0)

```
Cada agente tiene:
  - Su propio system_prompt en ingles (optimizado para tokens)
  - Instruccion final: "ALWAYS respond in Spanish"
  - Acceso al LLM compartido seleccionado por el usuario
  - Keywords para deteccion de intencion
  - Tools deterministas como primera opcion
  - LLM como fallback con datos del RAG

Agentes:
  1. RecipeAgent (Chef Ejecutivo)
     - Prompt: recetas, ingredientes, preparacion
     - Tools: buscar_receta, buscar_recetas_con_ingrediente, escalar_receta
  
  2. InventoryAgent (Jefe de Inventario)
     - Prompt: stock, caducidades, compras
     - Tools: productos_por_caducar, verificar_stock_bajo, registrar_compra
  
  3. MenuAgent (Chef de Planificacion)
     - Prompt: menus semanales, anti-desperdicio
     - Tools: consultar_menu_semanal, menu_anti_desperdicio, agregar_plato_menu
  
  4. WasteAgent (Controlador de Mermas)
     - Prompt: reportes, dashboard, clasificacion
     - Tools: reporte_mermas, registrar_merma, dashboard_sobrantes
  
  5. DocumentAgent (Oficial de Cumplimiento y Personal)
     - Prompt: documentos RAG + gestion de personal
     - Tools: buscar_documento, consultar_turno_hoy, consultar_personal_activo,
              consultar_personal_ausente, registrar_ausencia, registrar_permiso_rapido
```

## 5. Base de Datos

### 5.1 Tablas Principales

| Tabla | Descripcion | Novedades v2.0 |
|-------|-------------|-----------------|
| RecetasRAG | Recetas con busqueda semantica | - |
| Catalogo | Productos con vida util | +64 items con nombres CSV |
| Inventario | Stock de ingredientes | +referencias Catalogo corregidas |
| Mermas | Registro de desperdicios | +seed_mermas_realistas (160 registros) |
| MenuSemanalPro | Menus semanales | +28 platos (Lunes-Domingo) |
| Trabajadores | Personal del restaurante | +tipo_contrato, estado, ausencias |
| DocumentosRAG | Documentos cargados | +deteccion de duplicados |
| DocumentosTexto | Contenido completo de docs | +contenido_completo |
| Telemetry | Metricas de rendimiento | - |
| SobrantesReutilizables | Sobrantes por turno | +dashboard |

### 5.2 Trabajadores - Columnas nuevas

| Columna | Proposito |
|---------|-----------|
| tipo_contrato | fijo / temporal |
| estado | activo / reposo_medico / permiso_maternidad / vacaciones / suspendido |
| fecha_inicio_contrato | Inicio del contrato |
| fecha_fin_contrato | Fin (temporales) |
| fecha_inicio_ausencia | Inicio de baja |
| fecha_fin_ausencia | Fin de baja / retorno |
| motivo_ausencia | Razon de la ausencia |

## 6. Herramientas Nuevas (v2.0)

### 6.1 Compras Inteligentes
- `registrar_compra`: Lenguaje natural → "se compro 3 kintales de harina caduca 12-03-2027"
- Detecta: producto, cantidad, unidad, fecha caducidad, categoria, vida util

### 6.2 Permisos y Personal
- `registrar_permiso_rapido`: "juan saco permiso por paternidad 6 dias"
- `consultar_turno_hoy`: Personal activo hoy por turno
- `consultar_personal_activo`: Todos los activos
- `consultar_personal_ausente`: Bajas con fechas de retorno
- `registrar_ausencia`: Registro formal de ausencia
- `reincorporar_trabajador`: Alta tras ausencia

### 6.3 Inventario
- `dar_de_baja`: Rotura/dano → "plato sopero, 5, piezas, rotura, 25.00"
- `seed_mermas`: Genera datos realistas de mermas (160 registros/30 dias)

### 6.4 Registro de Mermas
- `registrar_merma`: Acepta formato clasico y lenguaje natural
  - "23 kilos de cerdo de merma"
  - "3 kg de pan se echo a perder"
  - "cebolla, 2.5, kg, se echo a perder, 1.50"

## 7. Alertas Cruzadas (Nuevo)

`agents/alertas.py` - Sistema que inyecta alertas proactivas al final de cada respuesta (solo primer mensaje):

| Tipo | Que verifica | Sugerencia |
|------|-------------|------------|
| Personal | Quien esta de baja, fecha retorno | - |
| Caducidad | Productos a 3 dias | Recetas para aprovecharlos |
| Stock bajo | < 5 unidades | Generar lista de compras |

## 8. Exportacion a Office (Mejorado)

- Exporta datos tabulares desde contexto guardado (no solo texto)
- PowerPoint acepta datos tabulares (antes solo recetas)
- Limpieza de Markdown antes de enviar a Word (formato profesional)
- Contexto guardado automaticamente en cada respuesta
- Deteccion automatica de tipo: Merma, Menu, Personal, Documento, etc.

## 9. GUI - Sidebar

| Boton | Funcion |
|-------|---------|
| Chat | Panel principal |
| Telemetria | Dashboard de uso |
| Configuracion | API Keys |
| Limpiar chat | Resetea historial y contexto |
| Documentacion | Genera Word + HTML desde resumen.md |
| Tema | Claro/Oscuro |

### 9.1 Selector de Agente
Barra dedicada "Agente:" entre el chat y el input. Opciones: Auto, Recetas, Inventario, Menu, Mermas, Documentos.

## 10. Prompts en Ingles (Optimizacion)

Todos los prompts del sistema estan en ingles para ahorrar ~28% de tokens. Cada prompt termina con `ALWAYS respond in Spanish.`

| Prompt | Tokens (antes) | Tokens (ahora) | Ahorro |
|--------|---------------|----------------|--------|
| RecipeAgent | ~120 | ~85 | -29% |
| InventoryAgent | ~90 | ~65 | -28% |
| MenuAgent | ~140 | ~100 | -29% |
| WasteAgent | ~130 | ~95 | -27% |
| DocumentAgent | ~150 | ~115 | -23% |
| Orchestrator | ~250 | ~180 | -28% |

## 11. Documentacion Automatizada

`documentacion.py` - Genera desde `resumen.md`:
- **Word** `.docx` (42 KB) - Portada profesional, encabezados, tablas, codigo con fondo oscuro
- **HTML** `.html` (44 KB) - Abre en navegador, Ctrl+P → guardar como PDF
- Sin dependencias externas (python-docx puro, sin WeasyPrint/GTK)
- Accesible desde el boton en la sidebar

## 12. Pruebas

### Suite de Tests (38 tests)

| Modulo | Tests |
|--------|-------|
| Guardrails | 10 |
| Ollama Provider | 4 |
| DSPy Optimizer | 8 |
| Multiagent | 13 |
| Integracion | 3 |

```bash
python -m pytest tests/ -v
```

## 13. Comandos Utiles

```bash
python main.py                           # Iniciar aplicacion
python documentacion.py                  # Generar documentacion Word + HTML
python -m pytest tests/ -v               # Ejecutar tests
```

---

*Ultima actualizacion: Mayo 2026*
*Version: ChefChat Pro v2.0*
