# ChefChat Pro

Asistente de escritorio con IA para gestion integral de restaurantes. Sistema multiagente donde cada agente tiene su propio prompt de sistema, usa el LLM seleccionado por el usuario, y responde solo con datos del RAG. Integracion con Microsoft Office, alertas cruzadas entre agentes, y gestion de personal.

## Novedades v2.0

- **Orquestador de Agentes**: Routing inteligente a agentes especializados (Recetas, Inventario, Menus, Mermas, Documentos)
- **Sistema Multiagente**: Planner + Executor con 5 agentes especializados para tareas complejas
- **Guardrails**: Proteccion contra inyeccion de prompts con 23 patrones de deteccion, validacion de entrada, rate limiting y filtrado de contenido
- **RAG**: Busqueda de documentos y recetas con expansion de consultas y sinonimos culinarios
- **Proveedores de IA**: OpenRouter, Azure OpenAI, Ollama (local gratuito), Gemini
- **HITL**: Aprobacion humana obligatoria para acciones criticas en Word/Excel/PowerPoint
- **Telemetria**: Registro de metricas y rendimiento con exportacion CSV/JSON
- **DSPy Optimizer**: Optimizacion de prompts con few-shot examples y feedback de relevancia
- **Dashboards Profesionales**: Exportacion a Excel con graficos (COM o fallback openpyxl/matplotlib)
- **Configuracion .env**: Soporte para variables de entorno para configuracion flexible
- **Inyeccion de Dependencias**: Container DI para mejor testabilidad

## Estructura

```
ChefChat/
├── main.py                    # Punto de entrada
├── requirements.txt           # Dependencias
├── chefchat.db                # Base de datos SQLite
├── .env.example               # Plantilla de configuracion
├── .gitignore                 # Archivos excluidos de git
│
├── agents/
│   ├── orchestrator.py        # Routing 9 prioridades + alertas
│   ├── multiagent.py          # 5 agentes con prompts + LLM
│   ├── tools.py               # 58 herramientas
│   ├── alertas.py             # Alertas cruzadas
│   └── mcp_client.py          # Word/Excel/PPT
│
├── core/                      # Componentes centrales
│   ├── config.py              # Configuracion y proveedores AI
│   ├── models.py              # Modelos Pydantic
│   ├── rag_classifier.py      # Clasificador RAG
│   ├── tool_contracts.py      # Contratos Pydantic para herramientas
│   └── di_container.py        # Inyeccion de dependencias
│
├── data/                      # Gestion de datos
│   ├── db_manager.py          # Gestor de base de datos
│   ├── rag_store.py           # Almacen RAG
│   ├── semantic_rag.py        # Busqueda semantica con FAISS
│   ├── dashboard_fallback.py  # Fallback para dashboards sin COM
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

## Instalacion

```bash
git clone <url>
cd ChefChat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Copiar configuracion
copy .env.example .env
# Editar .env con tus valores
```

## Uso

```bash
python main.py                  # Iniciar app
python documentacion.py         # Generar docs
python -m pytest tests/ -v      # Tests
```

## Proveedores IA

### OpenRouter (Principal)
1. Obtener API key en https://openrouter.ai
2. Configurar en la aplicacion (boton de llave) o en `.env`

### Ollama (Local Gratuito)
1. Instalar Ollama desde https://ollama.ai
2. Descargar modelo: `ollama pull llama3.2`
3. Seleccionar Ollama en la aplicacion o configurar `CHEFCHAT_AI_PROVIDER=ollama` en `.env`

### Azure OpenAI (Enterprise)
1. Crear recurso en Azure Portal
2. Configurar endpoint y API key en `.env`
3. Seleccionar en la aplicacion

### Google Gemini
1. Obtener API key en https://ai.google.dev
2. Configurar `CHEFCHAT_GEMINI_API_KEY` en `.env`

## Arquitectura

### Patron Principal
Clean Architecture + MVC + Orquestador de Agentes + Inyeccion de Dependencias

### Flujo de Procesamiento
1. Usuario envia peticion en GUI
2. Guardrails valida la entrada
3. Orchestrator clasifica intencion y detecta prioridad
4. DSPy Optimizer expande y optimiza prompt (si esta habilitado)
5. Routing a agente especializado o sistema multiagente
6. Respuesta formateada y enviada a GUI
7. Telemetria registrada

### Sistema Multiagente
- **Planner**: Analiza peticion compleja, asigna tareas por prioridad
- **Executor**: Ejecuta tareas, combina resultados, maneja errores
- **Agentes**: Recipe, Inventory, Menu, Waste, Document

### HITL (Human-in-the-Loop)
- Aprobacion obligatoria para acciones criticas en Word/Excel/PowerPoint
- QThread se pausa con `event.wait()` hasta aprobacion
- Preview en panel derecho de GUI
- Botones Aprobar/Rechazar con estilos visuales

## Seguridad

- API Keys almacenadas en keyring del SO o variables de entorno
- Guardrails intercepta prompts maliciosos
- Sandbox para pruebas MCP
- Zero credenciales en codigo
- Contratos Pydantic para validacion estricta de entrada/salida

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
- **79 tests pasan**, 3 skipped, 2 errors (aislamiento Qt en ejecucion masiva)
- Cobertura: Guardrails (10), Ollama (4), DSPy (8), Multiagent (13), Integracion (3), GUI (13), MCP (6), Modelos (12), Worker (5)

## Documentacion

- `docs_internos/resumen.md` - Resumen completo del proyecto
- `docs_internos/MANUAL.md` - Manual de usuario
- `docs_internos/architecture.md` - Arquitectura conceptual
- `docs_internos/INFORME_EVALUACION.md` - Informes de evaluacion

## Limitaciones Conocidas

### RAG
- Busqueda principal usa SQLite `LIKE` para keywords
- Busqueda semantica con FAISS disponible pero requiere `sentence-transformers`
- **Recomendacion**: Instalar `pip install faiss-cpu sentence-transformers` para busqueda semantica completa

### HITL
- UI de aprobacion implementada y funcional
- Requiere que el worker este en modo de espera para aprobacion

## Proximos Pasos

1. Implementar pipeline de evaluacion continua
2. Agregar GitHub Actions CI/CD workflow
3. Patrones de error boundary para degradacion graceful
4. GitHub Secret Scanning + Dependabot

## Licencia

MIT License - Ver archivo [LICENSE](LICENSE) para mas detalles.

---

*Ultima actualizacion: Mayo 2026*
