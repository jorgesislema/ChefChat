# ChefChat Pro

Asistente de escritorio con IA para gestion integral de restaurantes. Sistema multiagente donde cada agente tiene su propio prompt de sistema, usa el LLM seleccionado por el usuario, y responde solo con datos del RAG. Integracion con Microsoft Office, alertas cruzadas entre agentes, y gestion de personal.

## Novedades v2.0

- **5 agentes con prompts individuales**: Recipe, Inventory, Menu, Waste, Document. Cada uno con su `system_prompt` y acceso al LLM compartido.
- **Alertas cruzadas**: Al iniciar sesion, alerta sobre personal ausente, productos por caducar con sugerencias de recetas, y stock bajo.
- **Compras en lenguaje natural**: "se compro 3 kintales de harina caduca 12-03-2027"
- **Gestion de personal**: Registro de ausencias (reposo, maternidad, paternidad), consulta de turnos, personal activo/ausente.
- **Mermas realistas**: Generacion de datos de desperdicio con patrones de restaurante real (160 registros).
- **Menu semanal**: 28 platos cargados (Lunes-Domingo, 4 servicios/dia).
- **Exportacion mejorada**: Word/Excel/PPT con datos tabulares, limpieza de Markdown, contexto automatico.
- **Duplicados**: Deteccion al cargar documentos, no permite carga repetida.
- **Prompts en ingles**: ~28% ahorro de tokens, respuestas en espanol.
- **Documentacion**: Boton en sidebar genera Word + HTML profesional desde `resumen.md`.
- **Selector de agente**: Barra dedicada para elegir agente especifico o Auto.

## Estructura

```
ChefChat/
├── main.py                    # Entrada
├── documentacion.py           # Generador Word + HTML
│
├── agents/
│   ├── orchestrator.py        # Routing 9 prioridades + alertas
│   ├── multiagent.py          # 5 agentes con prompts + LLM
│   ├── tools.py               # 58 herramientas
│   ├── alertas.py             # Alertas cruzadas
│   └── mcp_client.py          # Word/Excel/PPT
│
├── core/                      # Config, modelos, seguridad
├── data/                      # DB manager, RAG store, menu semanal
├── gui/                       # PyQt6: main window, worker, telemetry
├── ops/                       # Guardrails (23 patrones)
├── prompting/                 # DSPy optimizer
├── scripts/                   # Data seeder, diagnostico
├── tests/                     # 38 tests
└── docs_internos/             # Documentacion
```

## Instalacion

```bash
git clone <url>
cd ChefChat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Uso

```bash
python main.py                  # Iniciar app
python documentacion.py         # Generar docs
python -m pytest tests/ -v      # Tests
```

## Proveedores IA

| Proveedor | Modelo |
|-----------|--------|
| DeepSeek | deepseek-chat |
| OpenRouter | minimax-2.7b |
| Ollama | llama3.2 (gratis) |
| OpenAI | gpt-4o |
| Claude | claude-3-5-sonnet |
| Gemini | gemini-1.5-flash |
| OpenCode | big-pickle (gratis) |

## Agentes

| Agente | Prompt | Funcion |
|--------|--------|---------|
| RecipeAgent | Executive Chef | Buscar/escalar recetas del RAG |
| InventoryAgent | Inventory Manager | Stock, caducidades, compras inteligentes |
| MenuAgent | Planning Chef | Menus semanales, anti-desperdicio |
| WasteAgent | Waste Controller | Dashboard, reportes, registro |
| DocumentAgent | Compliance Officer | Docs RAG + gestion de personal |

## GUI

| Elemento | Funcion |
|----------|---------|
| Selector Proveedor/Modelo | Elegir IA |
| Selector Agente | Auto o agente especifico |
| Chat | Burbujas HTML con temas |
| Sidebar | Chat, Telemetria, Config, Limpiar, Docs, Tema |
| Botones Office | Word, Excel, PowerPoint |
| HITL Bar | Aprobacion de acciones criticas |

## Seguridad

- API Keys en keyring del SO (nunca en codigo)
- Guardrails: 23 patrones anti-inyeccion
- Rate limiting, filtrado de contenido
- HITL para acciones Office

## Contratos Pydantic (30 modelos)

`core/models.py` — Validacion estricta de datos:

| Categoria | Modelos |
|-----------|---------|
| Personal | Trabajador, AusenciaInput, ReincorporarInput, PermisoRapidoInput |
| Mermas | MermaInput, MermaReporteOutput |
| Compras | CompraInput, BajaInventarioInput |
| Menu | MenuPlato, MenuSemanalOutput |
| Documentos | DocumentoRAGModel |
| Alertas | AlertasOutput |
| Inventario | Catalogo, Inventario (35 unidades), VistaCaducidad |
| Legacy | Ingrediente, Receta, Evento, AccionOffice, VentasHistoricas |

## Pruebas

51 tests pasan (38 core + 13 modelos).

## Licencia

Propietario - ChefChat Pro v2.0
