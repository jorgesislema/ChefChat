# ChefChat Pro v1.0 — Estructura del Codigo Fuente

## 1. Inventario de Archivos

### 1.1 Punto de Entrada

| Archivo | Lineas | Proposito |
|---------|--------|-----------|
| `main.py` | 23 | Punto de entrada de la aplicacion |

### 1.2 Modulo Agents (5494 lineas total)

| Archivo | Lineas | Clases Principales |
|---------|--------|-------------------|
| `agents/orchestrator.py` | 1785 | `Orchestrator` |
| `agents/multiagent.py` | 811 | `BaseAgent`, `RecipeAgent`, `InventoryAgent`, `MenuAgent`, `WasteAgent`, `DocumentAgent`, `Planner`, `Executor` |
| `agents/tools.py` | 2953 | 58 funciones de herramientas operativas |
| `agents/alertas.py` | 184 | `AlertManager` |
| `agents/mcp_client.py` | 374 | `MCPClient` |

### 1.3 Modulo Core (1086 lineas total)

| Archivo | Lineas | Clases Principales |
|---------|--------|-------------------|
| `core/config.py` | 163 | `ConfigManager`, `AIProvider` |
| `core/models.py` | 550 | 30+ modelos Pydantic |
| `core/di_container.py` | 84 | `DIContainer` |
| `core/tool_contracts.py` | 257 | Contratos de herramientas |
| `core/rag_classifier.py` | 259 | Clasificador de documentos |

### 1.4 Modulo Data (3436 lineas total)

| Archivo | Lineas | Clases Principales |
|---------|--------|-------------------|
| `data/db_manager.py` | 1675 | `DatabaseManager` |
| `data/rag_store.py` | 676 | `RAGStore` |
| `data/semantic_rag.py` | 265 | RAG semantico con FAISS |
| `data/menu_semanal.py` | 274 | `MenuSemanalManager` |
| `data/dashboard_fallback.py` | 546 | Dashboard fallback |

### 1.5 Modulo GUI (1913 lineas total)

| Archivo | Lineas | Clases Principales |
|---------|--------|-------------------|
| `gui/main_window.py` | 1381 | `MainWindow` |
| `gui/worker.py` | 200 | `Worker` |
| `gui/telemetry_view.py` | 332 | `TelemetryDashboard` |

### 1.6 Modulo Ops (224 lineas)

| Archivo | Lineas | Clases Principales |
|---------|--------|-------------------|
| `ops/guardrails.py` | 224 | `PromptInjectionDetector`, `InputValidator`, `RateLimiter`, `ContentFilter`, `Guardrails` |

### 1.7 Modulo Prompting (274 lineas)

| Archivo | Lineas | Clases Principales |
|---------|--------|-------------------|
| `prompting/dspy_optimizer.py` | 274 | `PromptOptimizer` |

### 1.8 Scripts (1211 lineas total)

| Archivo | Lineas | Proposito |
|---------|--------|-----------|
| `scripts/data_seeder.py` | 563 | Poblacion inicial de datos |
| `scripts/security_scan.py` | 308 | Escaneo de seguridad |
| `scripts/check_setup.py` | 257 | Verificacion de instalacion |
| `scripts/diagnose_keys.py` | 83 | Diagnostico de API keys |

## 2. Dependencias (requirements.txt)

```
PyQt6>=6.5
langchain-openai>=0.1.0
openai>=1.6.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
keyring>=24.0.0
python-dotenv>=1.0.0
python-dateutil>=2.8.0
pywin32>=306
pandas>=2.0.0
pytest>=8.0
pytest-qt>=4.2
```

## 3. Modelo de Datos

### 3.1 Modelos Pydantic (core/models.py)

**Legacy Models**:
- `Ingrediente`
- `Receta`
- `Evento`
- `AccionOffice`

**Core Models**:
- `Catalogo`
- `Inventario`
- `VistaCaducidad`
- `BitacoraDiaria`
- `VentasHistoricas`

**v2.0 Models**:
- `Trabajador`
- `AusenciaInput`
- `ReincorporarInput`
- `PermisoRapidoInput`
- `MermaInput`
- `MermaReporteOutput`
- `CompraInput`
- `BajaInventarioInput`
- `MenuPlato`
- `MenuSemanalOutput`
- `DocumentoRAGModel`
- `AlertasOutput`

### 3.2 Base de Datos (SQLite)

Ver `02_Arquitectura_y_Procesos_SOP/ARQUITECTURA.md` para diagrama ER completo.

## 4. Patrones de Diseno Implementados

| Patron | Ubicacion | Proposito |
|--------|-----------|-----------|
| Chain of Responsibility | `ops/guardrails.py` | Pipeline de validacion |
| Strategy | `agents/multiagent.py` | Agentes intercambiables |
| Template Method | `agents/multiagent.py:BaseAgent` | Comportamiento base de agentes |
| Facade | `agents/mcp_client.py:MCPClient` | Abstraccion de Office COM |
| Observer | `gui/worker.py` | Se�ales Qt para comunicación asyncrona |
| Service Locator | `core/di_container.py:DIContainer` | Inyeccion de dependencias |
| Data Transfer Object | `core/models.py` | Modelos Pydantic |
| Router | `agents/orchestrator.py` | Enrutamiento de 9 prioridades |

---

*Documento generado para ChefChat Pro v1.0 — Mayo 2026*
