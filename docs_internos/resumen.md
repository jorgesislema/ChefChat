# ChefChat Pro - Resumen del Proyecto

## 1. Vision General

ChefChat Pro es un asistente de escritorio para gestion de restaurantes que combina IA conversacional, agentes especializados, RAG (Retrieval-Augmented Generation) e integracion con Microsoft Office. Construido con PyQt6 para Windows, utiliza un patron de orquestador de agentes con aprobacion humana en el ciclo (HITL) para garantizar seguridad en operaciones criticas.

## 2. Estructura del Repositorio

```
ChefChat/
├── main.py                    # Punto de entrada de la aplicacion
├── requirements.txt           # Dependencias Python
├── chefchat.db                # Base de datos SQLite (17 tablas)
├── pyrightconfig.json         # Configuracion de type checking
├── .gitignore                 # Archivos excluidos de git
│
├── agents/                    # Agentes de IA y orquestacion
│   ├── orchestrator.py        # Orquestador principal con routing inteligente
│   ├── multiagent.py          # Sistema multiagente (Planner + Executor)
│   ├── tools.py               # Herramientas disponibles para agentes
│   └── [otros archivos]
│
├── core/                      # Componentes centrales
│   ├── config.py              # Configuracion y proveedores AI
│   ├── models.py              # Modelos Pydantic y contratos
│   └── [otros archivos]
│
├── data/                      # Gestion de datos y RAG
│   ├── menu_semanal.py        # CRUD MenuSemanalPro con RAG
│   └── [otros archivos]
│
├── data_source/               # Fuentes de datos externas
│   └── [documentos y recetas]
│
├── evaluation/                # Evaluaciones y metricas
│   └── [archivos de evaluacion]
│
├── gui/                       # Interaz grafica PyQt6
│   └── [componentes de UI]
│
├── ops/                       # Operaciones y seguridad
│   ├── guardrails.py          # Proteccion contra inyeccion de prompts
│   └── [otros modulos]
│
├── prompting/                 # Optimizacion de prompts
│   ├── dspy_optimizer.py      # Optimizador estilo DSPy
│   └── [otros archivos]
│
├── scripts/                   # Scripts de utilidad
│   ├── data_seeder.py         # Poblacion inicial de datos
│   ├── cargar_capacitacion.py # Carga de documentos de capacitacion
│   ├── diagnose_keys.py       # Diagnostico de API keys
│   ├── check_setup.py         # Verificacion de configuracion
│   └── security_scan.py       # Escaneo de seguridad
│
├── tests/                     # Pruebas unitarias e integracion
│   ├── conftest.py            # Configuracion de pytest
│   ├── test_new_modules.py    # 38 tests para modulos nuevos
│   ├── test_evaluation.py     # Tests de evaluacion
│   ├── test_export_mermas.py  # Tests de exportacion de mermas
│   ├── test_extraccion.py     # Tests de extraccion de datos
│   ├── test_menu_*.py         # Tests de menus y comidas
│   ├── test_orchestrator_flow.py # Tests de flujo del orquestador
│   ├── test_providers.py      # Tests de proveedores AI
│   ├── test_gui.py            # Tests de interfaz grafica
│   ├── test_mcp.py            # Tests de integracion MCP
│   ├── test_models.py         # Tests de modelos Pydantic
│   ├── test_worker.py         # Tests de worker threads
│   ├── golden_tests_ejemplo.json # Datos golden para tests
│   └── test_results_raw.txt   # Resultados crudos de tests
│
├── telemetry_exports/         # Exportaciones de telemetria
│   └── [archivos de telemetria]
│
└── docs_internos/             # Documentacion interna
    ├── resumen.md             # ESTE ARCHIVO - Resumen general
    ├── architecture.md        # Arquitectura conceptual
    ├── design.md              # Decisiones de diseno
    ├── implementation_plan.md # Plan de implementacion
    ├── MANUAL.md              # Manual de usuario
    └── [otros documentos]
```

## 3. Arquitectura del Sistema

### 3.1 Patron Principal
- **Clean Architecture + MVC + Orquestador de Agentes**
- Separacion estricta entre GUI (PyQt6), logica de negocio (Pydantic) e infraestructura (APIs, MCP)

### 3.2 Componentes Clave

| Componente | Responsabilidad | Tecnologia |
|------------|----------------|-------------|
| Orchestrator | Routing de peticiones a agentes especializados | LangChain + logica custom |
| Multiagent System | Planner + Executor con 5 agentes especializados | Patrón Planner/Executor |
| Guardrails | Proteccion contra inyeccion de prompts | 23 patrones de deteccion |
| RAG Engine | Busqueda semantica en documentos | SQLite + keyword matching |
| MCP Client | Integracion con Word/Excel | Servidor MCP externo |
| HITL Controller | Aprobacion humana antes de acciones criticas | threading.Event + Qt signals |
| DSPy Optimizer | Optimizacion de prompts con few-shot examples | Heuristic scoring |
| Telemetry | Registro de metricas y rendimiento | SQLite + export CSV/JSON |

### 3.3 Proveedores de IA

| Proveedor | Modelo | Costo | Uso |
|-----------|--------|-------|-----|
| OpenRouter | MiniMax 2.7 | Bajo | Principal |
| Ollama | llama3.2, llama3.1, mistral, etc. | Gratis | Local |
| Azure OpenAI | GPT-4, etc. | Variable | Enterprise |

## 4. Flujo de Procesamiento

### 4.1 Flujo Principal de Peticion

```
1. Usuario envia peticion en GUI
2. Guardrails valida la entrada (inyeccion, rate limiting, contenido)
3. Orchestrator clasifica la intencion y detecta prioridad
4. DSPy Optimizer expande y optimiza el prompt
5. Routing decision:
   ├── Consulta simple → Agente directo
   ├── Busqueda de recetas → RAG Engine + Agente Recetas
   ├── Gestion de inventario → Agente Inventario
   ├── Creacion de menu → Agente Menu
   ├── Analisis de mermas → Agente Waste
   ├── Documentos Office → MCP Client (con HITL)
   └── Tarea compleja → Multiagent System (Planner + Executor)
6. Respuesta formateada y enviada a GUI
7. Telemetria registrada
```

### 4.2 Flujo HITL (Human-in-the-Loop)

```
1. Agente genera accion critica (ej: crear archivo Word)
2. QThread emite senal request_approval a GUI
3. QThread se pausa con event.wait()
4. Usuario ve preview en panel derecho de GUI
5. Usuario hace clic en Aprobar/Rechazar
6. GUI llama a event.set() si aprobo
7. QThread se reanuda y ejecuta accion via MCP
8. Resultado guardado en SQLite
```

### 4.3 Sistema Multiagente

```
Planner:
  - Analiza peticion compleja
  - Asigna tareas por prioridad y keywords
  - Decide estrategia: single/parallel/sequential

Executor:
  - Ejecuta tareas asignadas
  - Combina resultados de multiples agentes
  - Maneja errores y reintentos

Agentes Especializados:
  1. Recipe Agent: Busqueda y generacion de recetas
  2. Inventory Agent: Gestion de inventario y stock
  3. Menu Agent: Creacion de menus semanales
  4. Waste Agent: Analisis y reduccion de mermas
  5. Document Agent: Generacion de documentos Office
```

## 5. Modulos Implementados

### 5.1 Guardrails (`ops/guardrails.py`)
- **Deteccion de inyeccion de prompts**: 23 patrones conocidos
- **Validacion de entrada**: Longitud maxima, caracteres prohibidos
- **Rate limiting**: 30 peticiones/minuto por usuario
- **Filtrado de contenido**: Bloqueo de contenido inapropiado

### 5.2 Ollama Provider (`core/config.py`, `agents/orchestrator.py`)
- **Proveedor local gratuito**: `http://localhost:11434/v1`
- **Modelos soportados**: llama3.2, llama3.1, mistral, codellama, phi3, gemma2
- **Costo cero**: Ideal para desarrollo y uso sin API keys

### 5.3 DSPy Optimizer (`prompting/dspy_optimizer.py`)
- **Few-shot prompt optimization**: Mejora prompts con ejemplos
- **Query expansion**: Sinonimos de alimentos y terminos culinarios
- **Relevance feedback**: Tracking de efectividad de prompts

### 5.4 Multiagent System (`agents/multiagent.py`)
- **Planner/Executor pattern**: Division inteligente de tareas
- **5 agentes especializados**: Recipe, Inventory, Menu, Waste, Document
- **Estrategias de ejecucion**: Single, parallel, sequential

## 6. Base de Datos

### 6.1 Tablas Principales (17 tablas en chefchat.db)

| Tabla | Descripcion |
|-------|-------------|
| RecetasRAG | Recetas con busqueda semantica |
| Inventario | Stock de ingredientes |
| Mermas | Registro de desperdicios |
| MenuSemanalPro | Menus semanales con RAG |
| Telemetry | Metricas de rendimiento |
| Conversaciones | Historial de chats |
| [otras 11 tablas] | Configuraciones, usuarios, etc. |

### 6.2 Limitaciones Actuales de RAG
- Usa SQLite `LIKE` para busqueda por keywords
- **No usa embeddings semanticos** → falla en consultas semanticas (ej: "BPM" no encuentra "Protocolos de Emergencia")
- **Mejora pendiente**: Implementar FAISS/Chroma + `sentence-transformers`

## 7. Seguridad

### 7.1 Protecciones Implementadas
- **API Keys**: Almacenadas en keyring del SO, nunca en codigo
- **Guardrails**: Intercepta prompts maliciosos antes de procesamiento
- **HITL**: Aprobacion obligatoria para acciones criticas
- **Sandbox**: Pruebas MCP limitadas a directorio seguro

### 7.2 Archivos Ignorados (.gitignore)
```
venv/
.env
*.db
*.sqlite
__pycache__/
*.log
```

## 8. Pruebas

### 8.1 Suite de Tests (38 tests principales)

| Modulo | Tests | Cobertura |
|--------|-------|-----------|
| Guardrails | 10 | Inyeccion, validacion, rate limiting |
| Ollama Provider | 4 | Configuracion, modelos, pricing |
| DSPy Optimizer | 8 | Few-shot, query expansion, feedback |
| Multiagent | 13 | Planner, Executor, agentes especializados |
| Integracion | 3 | Flujo completo con guardrails + multiagent |

### 8.2 Ejecucion de Tests
```bash
python -m pytest tests/ -v
```

## 9. Scripts de Utilidad

| Script | Funcion |
|--------|---------|
| `scripts/data_seeder.py` | Poblacion inicial de datos de prueba |
| `scripts/cargar_capacitacion.py` | Carga de documentos de capacitacion |
| `scripts/diagnose_keys.py` | Diagnostico de API keys configuradas |
| `scripts/check_setup.py` | Verificacion de configuracion completa |
| `scripts/security_scan.py` | Escaneo de seguridad del proyecto |

## 10. Limitaciones Conocidas

### 10.1 RAG
- **Problema**: Busqueda por keywords (`LIKE`) en lugar de embeddings semanticos
- **Impacto**: No encuentra documentos semanticamente relacionados
- **Solucion pendiente**: Implementar FAISS/Chroma + sentence-transformers

### 10.2 HITL
- **Problema**: Flag `requiere_hitl` existe pero UI de aprobacion inactiva
- **Impacto**: No hay cola de aprobacion ni mecanismo de pausa visible
- **Solucion pendiente**: Implementar UI de aprobacion y cola pendiente

### 10.3 Dependencias
- **Problema**: Algunas funciones requieren APIs externas
- **Impacto**: Costo operativo y dependencia de conectividad
- **Mitigacion**: Ollama como alternativa local gratuita

## 11. Proximos Pasos Prioritarios

1. **Implementar embeddings reales para RAG** (FAISS/Chroma + sentence-transformers)
2. **Implementar UI de aprobacion HITL** con cola pendiente
3. **Agregar contratos Pydantic** para validacion estricta de datos
4. **Soporte .env** para configuracion flexible
5. **GitHub Secret Scanning + Dependabot** antes de push a repositorio
6. **Documentacion adicional** para cada modulo

## 12. Comandos Utiles

### Ejecucion
```bash
python main.py                    # Iniciar aplicacion
python -m pytest tests/ -v        # Ejecutar tests
python scripts/check_setup.py     # Verificar configuracion
```

### Desarrollo
```bash
pip install -r requirements.txt   # Instalar dependencias
python -m pyright                 # Type checking
python scripts/security_scan.py   # Escaneo de seguridad
```

## 13. Contacto y Recursos

- **Documentacion interna**: `docs_internos/`
- **Tests**: `tests/`
- **Scripts**: `scripts/`
- **Base de datos**: `chefchat.db` (SQLite)
- **Configuracion**: `core/config.py`

---

*Ultima actualizacion: Mayo 2026*
*Version: ChefChat Pro v1.0*
