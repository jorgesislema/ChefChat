# ChefChat Pro v1.0 — Arquitectura del Sistema

## 1. Vision General

ChefChat Pro sigue una **Arquitectura Limpia (Clean Architecture)** combinada con **MVC** y un **Orquestador Multiagente** con **Inyeccion de Dependencias**.

### 1.1 Diagrama de Arquitectura

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Interfaz de Usuario (GUI)                     │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌───────────┐  │
│  │ MainWindow  │  │ Worker(QThread)│  │ Telemetry  │  │  HITL     │  │
│  │  (PyQt6)    │  │              │  │  Dashboard  │  │  Panel    │  │
│  └──────┬──────┘  └──────┬───────┘  └──────┬──────┘  └───────────┘  │
└─────────┼──────────────┼──────────────────┼──────────────────────────┘
          │              │                  │
          │              ▼                  │
          │     ┌────────────────┐          │
          │     │  Orchestrator  │          │
          │     │  (Router 9     │          │
          │     │   Prioridades) │          │
          │     └───┬────┬──────┘          │
          │         │    │                 │
          │         │    └──► Guardrails   │
          │         │         (Seguridad)  │
          │         ▼                      │
          │    ┌──────────┐               │
          │    │ Multiagent│               │
          │    │  System   │               │
          │    └──┬───┬────┘               │
          │       │   │                    │
          ▼       ▼   ▼                    ▼
    ┌────────┐ ┌──────┐ ┌──────────┐ ┌──────────┐
    │Recipe  │ │Inv.  │ │  Menu    │ │ Waste    │
    │Agent   │ │Agent │ │  Agent   │ │ Agent    │
    └───┬────┘ └──┬───┘ └────┬─────┘ └────┬─────┘
        │         │          │            │
        ▼         ▼          ▼            ▼
    ┌───────────────────────────────────────────┐
    │              Capa de Datos                │
    │  ┌────────┐ ┌──────────┐ ┌─────────────┐ │
    │  │DB      │ │RAG Store │ │ Semantic    │ │
    │  │Manager │ │          │ │ RAG (FAISS) │ │
    │  └────────┘ └──────────┘ └─────────────┘ │
    └───────────────────────────────────────────┘
```

### 1.2 Patron de Diseno

| Componente | Patron | Proposito |
|-----------|--------|-----------|
| Orchestrator | Router + Mediator | Enrutamiento inteligente de peticiones |
| Multiagent | Strategy + Composite | Agentes especializados intercambiables |
| BaseAgent | Template Method | Comportamiento base para todos los agentes |
| DIContainer | Service Locator | Inyeccion de dependencias global |
| Guardrails | Chain of Responsibility | Pipeline de validacion de seguridad |
| MCPClient | Facade | Abstraccion de Office COM |
| Worker | Observer (señales Qt) | Comunicacion asincrona GUI-backend |
| Models (Pydantic) | Data Transfer Object | Validacion estricta de datos |

## 2. Sistema de Orquestacion

### 2.1 Flujo de Procesamiento

```
Usuario envia peticion en GUI
        │
        ▼
┌──────────────────────┐
│  1. Guardrails       │
│  - Deteccion de      │
│    inyeccion (23     │
│    patrones)          │
│  - Rate limiting     │
│  - Filtro de         │
│    contenido          │
│  - Validacion de     │
│    entrada            │
└──────────┬───────────┘
           │ (SI es seguro)
           ▼
┌──────────────────────┐
│  2. Orchestrator     │
│  Clasifica intencion │
│  (9 prioridades)     │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  3. DSPy Optimizer   │
│  (opcional)          │
│  - Expansion de      │
│    consulta          │
│  - Few-shot examples │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  4. Routing          │
│  - Agente forzado    │
│  - Agente detectado  │
│  - LLM directo       │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  5. Procesamiento    │
│  - Herramientas      │
│  - RAG query         │
│  - Respuesta LLM     │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  6. Post-proceso     │
│  - Alertas cruzadas  │
│  - Contexto Office   │
│  - Telemetria        │
└──────────┬───────────┘
           │
           ▼
       GUI (respuesta)
```

### 2.2 Sistema de 9 Prioridades

| Prioridad | Tipo | Descripcion | Ejemplo |
|-----------|------|-------------|---------|
| PRI 1 | Exportacion Office | Exportacion directa a Word/Excel/PPT | "a Excel con estos datos" |
| PRI 2 | Menu Semanal | Gestion del menu de la semana | "configurar menu semanal" |
| PRI 3 | Busqueda RAG | Busqueda en documentos cargados | "busca documento sobre BPM" |
| PRI 3.5 | Personal | Consultas de personal y ausencias | "personal activo hoy" |
| PRI 4 | Receta por ID | Busqueda exacta por codigo | "PLF-050" |
| PRI 5 | Menu por Ingredientes | Sugerir menu con ingredientes disponibles | "menu con pollo" |
| PRI 6 | Mermas | Registro y consulta de desperdicios | "registrar merma" |
| PRI 7 | Receta por Nombre | Busqueda por nombre en RAG | "busca receta Sopa de Tomate" |
| PRI 8 | Herramientas Detectables | 23 herramientas operativas | "registrar incidencia" |
| PRI 9 | LLM Directo | Fallback a respuesta generativa | "explica que hace el sistema" |

### 2.3 Agentes Especializados

| Agente | Rol | Sistema de Prompt | Herramientas Clave |
|--------|-----|------------------|-------------------|
| RecipeAgent | Executive Chef | Sistema en ingles (recetas) | buscar_receta, escalar_receta, sugerir_menu |
| InventoryAgent | Inventory Manager | Sistema en ingles (inventario) | stock_bajo, caducidad, registrar_compra |
| MenuAgent | Planning Chef | Sistema en ingles (menu) | menu_semanal, menu_anti_desperdicio |
| WasteAgent | Waste Controller | Sistema en ingles (mermas) | reporte_mermas, dashboard_sobrantes |
| DocumentAgent | Compliance Officer | Sistema en ingles (docs/personal) | buscar_documento, consultar_personal |

## 3. Base de Datos

### 3.1 Diagrama Entidad-Relacion

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐
│  Catalogo   │───<│  Inventario  │    │  Recetas     │
│ (productos) │    │  (stock)     │    │  (recetario) │
└─────────────┘    └──────────────┘    └──────┬───────┘
       │                                      │
       │         ┌──────────────┐             │
       │         │  Mermas      │             │
       ├────────>│  (desperdicio)│             │
       │         └──────────────┘             │
       │         ┌──────────────┐             │
       │         │ OrdenesCompra│             │
       ├────────>│  (compras)   │             │
       │         └──────────────┘             │
       │         ┌──────────────┐             │
       └────────>│  MenuSemanal │◄────────────┘
                 └──────────────┘
                 ┌──────────────┐
                 │  Trabajadores│
                 └──────┬───────┘
                        │
                 ┌──────▼───────┐
                 │  Sobrantes   │
                 └──────────────┘
```

### 3.2 Tablas Principales

| Tabla | Registros Tipicos | Proposito |
|-------|------------------|-----------|
| Catalogo | 35+ productos | Catalogo de productos con vida util |
| Inventario | 100+ lotes | Stock actual con fechas de caducidad |
| Recetas | 50+ platos | Recetario con ingredientes y costos |
| Mermas | 160+ registros | Historial de desperdicios |
| OrdenesCompra | Ilimitado | Ordenes de compra a proveedores |
| MenuSemanalPro | 28 platos/semana | Menu semanal (7 dias x 4 servicios) |
| Trabajadores | Ilimitado | Gestion de personal |
| DocumentosRAG | Ilimitado | Documentos cargados al sistema |
| Telemetria | Ilimitado | Metricas de rendimiento y costos |

## 4. Sistema RAG

### 4.1 Pipeline de Ingestion

```
Documento entrante (PDF, DOCX, TXT, CSV, XLSX)
        │
        ▼
┌──────────────────┐
│ 1. Clasificacion │
│ (rag_classifier) │
│ - receta         │
│ - catalogo       │
│ - lotes          │
│ - manual_bpm     │
│ - generico       │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 2. Almacenamiento│
│ (rag_store)      │
│ - Deteccion de   │
│   duplicados     │
│ - Preview + full │
│   text           │
│ - Palabras clave │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 3. Indexacion    │
│ (semantic_rag)   │
│ - FAISS vectors  │
│   (si disponible)│
│ - SimpleEmbedder │
│   (fallback)     │
│ - Sinonimos      │
│   culinarios     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 4. Busqueda      │
│ - LIKE keywords  │
│   (primaria)     │
│ - Vector search  │
│   (secundaria)   │
│ - Expansion de   │
│   consultas      │
└──────────────────┘
```

### 4.2 Busqueda Semantica (FAISS)

Cuando `sentence-transformers` esta instalado:

1. Se genera un embedding del documento al ingresarlo
2. Los embeddings se almacenan en un indice FAISS
3. La busqueda convierte la consulta a vector y busca por similitud coseno
4. Los resultados se combinan con la busqueda por keywords

**Requerimiento opcional**:
```bash
pip install faiss-cpu sentence-transformers
```

## 5. Integracion con Microsoft Office

### 5.1 Arquitectura MCP

```
┌──────────┐     ┌───────────┐     ┌───────────┐
│  GUI     │────>│  MCPClient│────>│  COM      │
│ (Worker) │     │  (Facade) │     │  (Office) │
└──────────┘     └───────────┘     └───────────┘
                       │
                       ▼
                ┌───────────────┐
                │  Sandbox Path │
                │ C:\Temp\      │
                │ ChefChat_     │
                │ Sandbox\      │
                └───────────────┘
```

### 5.2 Plantillas

El sistema soporta plantillas de Office con variables `{{variable}}` para insercion dinamica de contenido.

### 5.3 Fallback de Dashboard

Cuando Excel COM no esta disponible, se usa openpyxl + matplotlib como fallback para generar dashboards profesionales.

## 6. Seguridad

### 6.1 Pipeline de Validacion

```
Entrada del usuario
        │
        ▼
┌──────────────────────┐
│ InputValidator       │
│ - Max 5000 chars     │
│ - Max 500 palabras   │
│ - Trim whitespace    │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ PromptInjection      │
│ Detector             │
│ - 23 patrones        │
│   de inyeccion       │
│ - 16 patrones        │
│   sospechosos        │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ ContentFilter        │
│ - URLs bloqueadas    │
│ - IPs bloqueadas     │
│ - File paths         │
│ - Shell commands     │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ RateLimiter          │
│ - 5 requests/60s     │
│   (default)          │
│ - Sliding window     │
└──────────┬───────────┘
           ▼
     (SAFE/SUSPICIOUS/BLOCKED)
```

## 7. Optimizacion DSPy

El optimizador de prompts (estilo DSPy) proporciona:

1. **Few-shot examples**: Almacena ejemplos exitosos para mejorar respuestas futuras
2. **Expansion de consultas**: Agrega sinonimos culinarios para mejorar busqueda RAG
3. **Feedback de relevancia**: Evalua la relevancia de las respuestas generadas

## 8. Telemetria y Monitoreo

### 8.1 Metricas Registradas

| Metrica | Descripcion |
|---------|-------------|
| modelo_usado | Modelo de IA utilizado |
| input_tokens | Tokens de entrada |
| output_tokens | Tokens de salida |
| costo_total_usd | Costo estimado de la operacion |
| tipo_operacion | Tipo de operacion (tool_call, llm_directo, etc.) |
| duracion_segundos | Tiempo de procesamiento |
| exito | Booleano de exito/fallo |

### 8.2 Calculo de Costos

Los costos se calculan usando un diccionario de precios por millon de tokens para cada modelo:

```python
PRECIOS_POR_MODELO = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
    "deepseek-chat": {"input": 0.14, "output": 0.28},
    "llama3.2": {"input": 0.00, "output": 0.00},  # Local (gratis)
    ...
}
```

---

*Documento generado para ChefChat Pro v1.0 — Mayo 2026*
