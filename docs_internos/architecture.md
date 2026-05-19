# Documento de Diseño Conceptual: ChefChat (AI Restaurant Assistant)

## 1. Resumen Ejecutivo

ChefChat es una aplicacion de escritorio Windows construida con PyQt6 que orquesta multiples agentes de IA para la gestion de restaurantes. La arquitectura combina Clean Architecture con MVC y un Patron de Orquestador de Agentes, separando estrictamente la GUI, la logica de negocio y la infraestructura. El sistema consume LLM via OpenRouter (MiniMax 2.7) para inferencia y utiliza LangChain/LlamaIndex para el enrutamiento de agentes y RAG hibrido. La conectividad a Microsoft Office se achieve mediante un cliente MCP con una maquina de estados HITL obligatoria: cualquier accion de escritura en Word o Excel requiere aprobacion explicita del usuario antes de ejecutarse, utilizando threading.Event para pausar el QThread y signals de Qt para comunicar con la GUI. Los secretos (API keys) se almacenan exclusivamente en el Keyring del sistema operativo, garantizando zero credenciales en codigo.

## 2. Estilo Arquitectónico

**Patron**: Clean Architecture integrado con MVC y Patrón de Orquestador de Agentes.
**Razon**: Separacion estricta entre la GUI (PyQt6), la logica del negocio (Contratos Pydantic) y la infraestructura (OpenRouter, MCP).

## 3. Componentes Principales

| Componente | Responsabilidad | Tecnologia |
|------------|----------------|-------------|
| Controlador de Hilos (Worker) | Aislar la inferencia de la GUI con soporte HITL | QThread + threading.Event |
| Agente Supervisor | Clasificar la intencion del usuario | LangChain / LlamaIndex |
| Agente RAG Hibrido | Recuperar Recetas y BPM | Vector Store local + Keyword Search |
| Cliente MCP Office | Leer/Escribir en Word y Excel | Integracion con servidor MCP (ej. Arcade/Softeria) |
| Repositorio / Memoria | Persistencia de eventos y estado | SQLite + sqlite3 |
| Gestor de Secretos | Proteger API Keys de OpenRouter/LangSmith | Libreria keyring del OS |

## 4. Flujo de Datos y Maquina de Estados (HITL)

1. Usuario envia peticion en la GUI.
2. Se lanza un QThread. El Agente Supervisor evalua la peticion.
3. **Rama RAG:** Si es consulta, extrae datos, el LLM formatea y envia la senal a la GUI.
4. **Rama MCP (Accion Critica):** Si implica crear un menu en Word:
   - El Agente genera la estructura.
   - El QThread emite una senal request_approval a la GUI y llama a event.wait() (se pausa).
   - El usuario visualiza la accion en el panel derecho de la GUI y hace clic en Aprobar.
   - La GUI llama a event.set(), el hilo se reanuda y el MCP ejecuta la escritura en el Sandbox.
5. El resultado final se guarda en SQLite.

## 5. Stack Tecnologico

### 5.1 GUI y Orquestacion

| Tecnologia | Justificacion |
|------------|----------------|
| PyQt6 | Soporte nativo para senales y manejo robusto de hilos en Windows |
| LangChain / LlamaIndex | Framework estandar para el enrutamiento de agentes y RAG |

### 5.2 IA y Datos

| Tecnologia | Justificacion |
|------------|----------------|
| OpenRouter (MiniMax 2.7) | LLM principal: Alto contexto, excelente tool calling y bajo costo |
| Pydantic | Contratos de datos estrictos; evita alucinaciones en el paso de variables al MCP |
| SQLite | Persistencia de historial conversacional y metadatos de eventos |

### 5.3 Seguridad y Entorno (CRITICO)

| Directiva | Implementacion |
|------------|----------------|
| Archivos ignorados | El archivo .gitignore DEBE excluir venv/, .env, *.db, *.sqlite, __pycache__/ y *.log |
| Cero Credenciales | Prohibido quemar contrasenas en el codigo. Uso obligatorio de keyring |
| Entorno Sandbox | Las pruebas MCP se limitan a un directorio C:\Temp\ChefChat_Sandbox\ |

## 6. Modelo de Datos y Contratos (Pydantic)

### 6.1 Contrato Evento

- id_evento: UUID
- tipo: str (boda, corporativo)
- presupuesto: float
- estado: str (boceto, aprobado)

### 6.2 Contrato AccionMCP

- herramienta: str (word, excel)
- ruta_archivo: str
- payload: dict
- requiere_aprobacion: bool (Siempre True para escritura)

## 7. Patrones de Diseño

| Patron | Aplicacion | Beneficio |
|--------|------------|------------|
| Modelo-Vista-Controlador (MVC) | Separacion del UI y Logica | Facilita pruebas y evolucion |
| Observer (Senales Qt) | Comunicacion Worker -> GUI | Evita congelamiento de la ventana |
| State Machine (Eventos) | Pausa para aprobacion HITL | Seguridad total antes de modificar archivos |
| Adapter | Conector hacia OpenRouter y MCP | Permite cambiar de LLM sin reescribir codigo |

## 8. Siguientes Pasos

El Agente 3 (Diseno Visual) utilizara este documento para definir la Pantalla Dividida y la ubicacion del boton de Aprobacion (HITL).