# Documento de Diseño Técnico Detallado: ChefChat

## 1. Resumen Ejecutivo

ChefChat es una aplicacion de escritorio Windows construida sobre Python 3.10+ con PyQt6 como interfaz grafica. La arquitectura sigue el Patron de Orquestador de Agentes combinada con Clean Architecture, aislando la logica de negocio en capas independientes. La comunicacion con modelos LLM se realiza exclusivamente via OpenRouter API (modelo MiniMax 2.7), sin inferencia local. La capa de agentes utiliza LangChain/LlamaIndex para el enrutamiento de intenciones y la recuperacion RAG hibrida. La comunicacion con Microsoft Office se achieve mediante un cliente MCP que ejecuta acciones de lectura y escritura en un entorno Sandbox. Toda la gestion de credenciales se realiza mediante la libreria keyring del sistema operativo, garantizando zero claves en codigo o archivos de configuracion.

## 2. Contratos de Datos (Pydantic Models)

### 2.1 Dominio del Restaurante

```python
class Ingrediente(BaseModel):
    nombre: str
    cantidad: float
    unidad: str

class Receta(BaseModel):
    id_receta: str
    nombre: str
    ingredientes: List[Ingrediente]
    alergenos: List[str]
    costo_estimado: float

class Evento(BaseModel):
    id_evento: str
    tipo_evento: str
    fecha: str
    presupuesto: float
    estado_aprobacion: str = "pendiente"
```

### 2.2 Contrato MCP (Acciones)

```python
class AccionOffice(BaseModel):
    herramienta: Literal["word", "excel"]
    operacion: Literal["leer", "escribir", "crear"]
    ruta_archivo: str
    payload: dict
    requiere_hitl: bool = True
```

## 3. Interfaces y Contratos Tecnicos

### 3.1 Proveedor LLM (Adapter Pattern)

Responsabilidad: Conectar con OpenRouter API (MiniMax 2.7) e inyectar el contexto RAG y las herramientas MCP.

Metodos:
- `__init__(api_key: str)`
- `generar_respuesta(historial: List[dict], herramientas: List[Tool]) -> str`
- `extraer_json_estructurado(prompt: str, schema: Type[BaseModel]) -> dict`
- `streaming_callback(chunk: str) -> None`

### 3.2 Cliente MCP (Office)

Responsabilidad: Enviar comandos a un servidor MCP local (Arcade/Softeria).

Metodos:
- `conectar_servidor(ruta_mcp: str) -> bool`
- `ejecutar_herramienta(accion: AccionOffice) -> dict`
- `leer_excel(ruta: str, hoja: str) -> DataFrame`
- `escribir_excel(ruta: str, datos: dict) -> bool`
- `crear_word(ruta: str, contenido: str) -> bool`

### 3.3 Worker de Inferencia (QThread + HITL)

Responsabilidad: Ejecutar la cadena de LangChain sin bloquear la UI y manejar la Maquina de Estados.

Atributos clave:
- `hitl_event: threading.Event()`
- `accion_pendiente: Optional[AccionOffice]`

Senales Qt:
- `chunk_recibido(str)` — Para streaming en el chat
- `requiere_aprobacion(AccionOffice)` — Pausa el hilo
- `accion_completada(str)`
- `error_occurred(str)`

Logica HITL:
Si el LLM invoca una herramienta de escritura MCP, el Worker emite la senal `requiere_aprobacion`, invoca `self.hitl_event.wait()`. Cuando la GUI llama a `aprobar_accion()`, ejecuta `self.hitl_event.set()` y el Worker continua con la llamada al Cliente MCP.

## 4. Modelo de Datos (SQLite - Memoria)

### 4.1 Tabla historial_chat

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| id | INTEGER PRIMARY KEY | Autoincremento |
| session_id | TEXT | Identificador de sesion |
| rol | TEXT | user, assistant, system, tool |
| contenido | TEXT | Contenido del mensaje |
| timestamp | DATETIME | Marca temporal |

### 4.2 Tabla eventos

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| id_evento | TEXT PRIMARY KEY | UUID del evento |
| tipo_evento | TEXT | boda, corporativo, etc |
| fecha | TEXT | ISO 8601 |
| presupuesto | REAL | Decimal |
| estado_aprobacion | TEXT | pendiente, aprobado, rechazado |

## 5. Estructura de Modulos (Directorio Raiz)

```
ChefChat/
├── core/
│   ├── models.py          # Contratos Pydantic
│   ├── config.py          # Logica de Keyring y settings
│   └── security.py        # Validaciones de Sandbox
├── agents/
│   ├── orchestrator.py    # Logica LangChain / Router
│   └── mcp_client.py      # Conector al servidor MCP de Office
├── gui/
│   ├── main_window.py     # QSplitter y layouts
│   ├── worker.py          # QThread y threading.Event
│   └── dialogs.py         # Modal de API Keys
├── data/
│   └── db_manager.py      # SQLite
├── docs_internos/         # Documentos de arquitectura (Ignorados en Git)
├── main.py
├── .gitignore
└── requirements.txt
```

## 6. Seguridad y Configuracion (CRITICO)

**Cero Env/Text Keys**: La API Key de OpenRouter NO se guarda en .env ni config.json. Se usa la libreria keyring:

```python
keyring.set_password("ChefChat", "openrouter_key", api_key)
keyring.get_password("ChefChat", "openrouter_key")
```

**Entorno Sandbox**: mcp_client.py debe validar que ruta_archivo siempre comience con `C:\Temp\ChefChat_Sandbox\` en modo desarrollo. Toda operacion de escritura debe pasar por esta validacion antes de ejecutarse.

**Directiva Git**: El archivo .gitignore debe contener explicitamente:

```
venv/
__pycache__/
*.db
*.sqlite
.env
logs/
docs_internos/
*.log
C:\Temp\ChefChat_Sandbox\
```

## 7. Manejo de Errores

| Codigo | Tipo | Manejo (GUI) |
|--------|------|-------------|
| ERR-API | Autenticacion/OpenRouter | Mostrar modal de "Reingresar API Key" |
| ERR-MCP | Servidor Office caido | Mostrar alerta roja en Panel Derecho |
| ERR-VAL | Pydantic ValidationError | El Orquestador reintenta la llamada al LLM (max 2 veces) |
| ERR-SANDBOX | Ruta fuera del Sandbox | Bloquear operacion, mostrar error en chat |

## 8. Siguientes Pasos

El Agente 5 (Planificacion) usara esta estructura para generar el desglose de tareas, priorizando la creacion del entorno, el QThread con HITL y la integracion con OpenRouter en el MVP.