# ChefChat Pro 🍳

Asistente de escritorio con IA para gestion integral de restaurantes. Combina agentes especializados, RAG, proteccion contra inyeccion de prompts e integracion con Microsoft Office con aprobacion humana en el ciclo (HITL).

## Caracteristicas

- **Orquestador de Agentes**: Routing inteligente a agentes especializados (Recetas, Inventario, Menus, Mermas, Documentos)
- **Sistema Multiagente**: Planner + Executor con 5 agentes especializados para tareas complejas
- **Guardrails**: Proteccion contra inyeccion de prompts con 23 patrones de deteccion, validacion de entrada, rate limiting y filtrado de contenido
- **RAG**: Busqueda de documentos y recetas con expansion de consultas y sinonimos culinarios
- **Proveedores de IA**: OpenRouter, Azure OpenAI, Ollama (local gratuito)
- **HITL**: Aprobacion humana obligatoria para acciones criticas en Word/Excel
- **Telemetria**: Registro de metricas y rendimiento con exportacion CSV/JSON
- **DSPy Optimizer**: Optimizacion de prompts con few-shot examples y feedback de relevancia

## Estructura del Proyecto

```
ChefChat/
├── main.py                    # Punto de entrada
├── requirements.txt           # Dependencias
├── chefchat.db                # Base de datos SQLite
├── .gitignore                 # Archivos excluidos de git
│
├── agents/                    # Agentes de IA
│   ├── orchestrator.py        # Orquestador principal
│   ├── multiagent.py          # Sistema multiagente (Planner + Executor)
│   ├── tools.py               # Herramientas disponibles
│   └── mcp_client.py          # Cliente MCP para Office
│
├── core/                      # Componentes centrales
│   ├── config.py              # Configuracion y proveedores AI
│   ├── models.py              # Modelos Pydantic
│   └── rag_classifier.py      # Clasificador RAG
│
├── data/                      # Gestion de datos
│   ├── db_manager.py          # Gestor de base de datos
│   ├── rag_store.py           # Almacen RAG
│   └── menu_semanal.py        # CRUD MenuSemanalPro
│
├── data_source/               # Fuentes de datos externas
│   ├── 1_recetas/             # Recetas en CSV
│   └── 3_inventario/          # Catalogo e inventario
│
├── evaluation/                # Evaluaciones y metricas
│
├── gui/                       # Interfaz grafica PyQt6
│   ├── main_window.py         # Ventana principal
│   ├── worker.py              # Worker thread con HITL
│   └── telemetry_view.py      # Vista de telemetria
│
├── ops/                       # Operaciones y seguridad
│   └── guardrails.py          # Proteccion contra inyeccion
│
├── prompting/                 # Optimizacion de prompts
│   └── dspy_optimizer.py      # Optimizador estilo DSPy
│
├── scripts/                   # Scripts de utilidad
│   ├── data_seeder.py         # Poblacion inicial de datos
│   ├── cargar_capacitacion.py # Carga de documentos
│   ├── diagnose_keys.py       # Diagnostico de API keys
│   ├── check_setup.py         # Verificacion de configuracion
│   └── security_scan.py       # Escaneo de seguridad
│
├── tests/                     # Pruebas unitarias e integracion
│   ├── conftest.py            # Configuracion de pytest
│   ├── test_new_modules.py    # 38 tests para modulos nuevos
│   ├── test_gui.py            # Tests de interfaz grafica
│   ├── test_mcp.py            # Tests de integracion MCP
│   ├── test_models.py         # Tests de modelos Pydantic
│   ├── test_worker.py         # Tests de worker threads
│   └── [otros tests]          # Tests de evaluacion, menus, etc.
│
├── telemetry_exports/         # Exportaciones de telemetria
│
└── docs_internos/             # Documentacion interna
    ├── resumen.md             # Resumen general del proyecto
    ├── architecture.md        # Arquitectura conceptual
    ├── MANUAL.md              # Manual de usuario
    └── [otros documentos]     # Evaluaciones, seguridad, etc.
```

## Requisitos

- Python 3.13+
- Windows 10/11
- PyQt6
- OpenRouter API key (opcional, Ollama es gratuito)

## Instalacion

```bash
# Clonar repositorio
git clone <url-del-repo>
cd ChefChat

# Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

## Uso

```bash
# Iniciar aplicacion
python main.py

# Ejecutar tests
python -m pytest tests/ -v

# Verificar configuracion
python scripts/check_setup.py

# Escaneo de seguridad
python scripts/security_scan.py
```

## Configuracion de Proveedores de IA

### OpenRouter (Principal)
1. Obtener API key en https://openrouter.ai
2. Configurar en la aplicacion (boton de llave)

### Ollama (Local Gratuito)
1. Instalar Ollama desde https://ollama.ai
2. Descargar modelo: `ollama pull llama3.2`
3. Seleccionar Ollama en la aplicacion

### Azure OpenAI (Enterprise)
1. Crear recurso en Azure Portal
2. Configurar endpoint y API key
3. Seleccionar en la aplicacion

## Arquitectura

### Patron Principal
Clean Architecture + MVC + Orquestador de Agentes

### Flujo de Procesamiento
1. Usuario envia peticion en GUI
2. Guardrails valida la entrada
3. Orchestrator clasifica intencion y detecta prioridad
4. DSPy Optimizer expande y optimiza prompt
5. Routing a agente especializado o sistema multiagente
6. Respuesta formateada y enviada a GUI
7. Telemetria registrada

### Sistema Multiagente
- **Planner**: Analiza peticion compleja, asigna tareas por prioridad
- **Executor**: Ejecuta tareas, combina resultados, maneja errores
- **Agentes**: Recipe, Inventory, Menu, Waste, Document

### HITL (Human-in-the-Loop)
- Aprobacion obligatoria para acciones criticas en Word/Excel
- QThread se pausa con `event.wait()` hasta aprobacion
- Preview en panel derecho de GUI

## Seguridad

- API Keys almacenadas en keyring del SO
- Guardrails intercepta prompts maliciosos
- Sandbox para pruebas MCP
- Zero credenciales en codigo

## Pruebas

```bash
# Todos los tests
python -m pytest tests/ -v

# Tests especificos
python -m pytest tests/test_new_modules.py -v
python -m pytest tests/test_gui.py -v
python -m pytest tests/test_mcp.py -v
```

### Resultados Actuales
- **78 tests pasan**, 4 skipped, 2 errors (autenticacion externa)
- Cobertura: Guardrails (10), Ollama (4), DSPy (8), Multiagent (13), Integracion (3)

## Documentacion

- `docs_internos/resumen.md` - Resumen completo del proyecto
- `docs_internos/MANUAL.md` - Manual de usuario
- `docs_internos/architecture.md` - Arquitectura conceptual
- `docs_internos/INFORME_EVALUACION.md` - Informes de evaluacion

## Limitaciones Conocidas

### RAG
- Usa SQLite `LIKE` para busqueda por keywords
- No usa embeddings semanticos → falla en consultas semanticas
- **Mejora pendiente**: Implementar FAISS/Chroma + sentence-transformers

### HITL
- Flag `requiere_hitl` existe pero UI de aprobacion inactiva
- **Mejora pendiente**: Implementar UI de aprobacion y cola pendiente

## Proximos Pasos

1. Implementar embeddings reales para RAG
2. Implementar UI de aprobacion HITL con cola pendiente
3. Agregar contratos Pydantic para validacion estricta
4. Soporte .env para configuracion flexible
5. GitHub Secret Scanning + Dependabot

## Licencia

Propietario - ChefChat Pro v1.0

---

*Ultima actualizacion: Mayo 2026*
