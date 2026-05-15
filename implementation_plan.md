# Documento de Planificacion de Implementacion: ChefChat

## 1. Resumen Ejecutivo

ChefChat se implementara mediante un enfoque agile en 4 sprints de una semana cada uno, totalizando aproximadamente 4 semanas hasta alcanzar un MVP funcional. El nucleo de la aplicacion se construye sobre Python 3.10+ con PyQt6 para la interfaz de escritorio, conectandose exclusivamente a OpenRouter (modelo MiniMax 2.7) para inferencia en la nube. La automatizacion de Microsoft Office se realiza mediante un cliente MCP que opera dentro de un entorno Sandbox, garantizando que ninguna accion de escritura se ejecute sin la aprobacion explicita del usuario a traves del mecanismo HITL (Human-in-the-Loop). El plan prioriza la seguridad desde el inicio: la estructura de directorios, el .gitignore y la integracion con Keyring constituyen las primeras tareas del proyecto, antes de cualquier desarrollo de logica de negocio o interfaz grafica.

## 2. Alcance del Proyecto

### 2.1 Funcionalidades Incluidas (MVP)

- Gestion segura de API Keys mediante Keyring del sistema operativo
- Interfaz PyQt6 en pantalla dividida (Split-Screen) de 40/60 por ciento
- Conexion con OpenRouter (MiniMax 2.7) via LangChain para generacion de respuestas
- Sistema HITL basado en QThread y threading.Event para aprobacion de acciones criticas
- Integracion cliente MCP para lectura y escritura de archivos Word y Excel en Sandbox
- Almacenamiento de historial conversacional en SQLite local
- RAG hibrido (semantico + keyword) para recuperacion de recetas y manuales BPM

### 2.2 Funcionalidades Excluidas (Futuras)

- DSPy para optimizacion dinamica en tiempo real (reservado para fase de produccion)
- Base de datos vectorial en la nube (se usara SQLite local con busqueda hibrida)
- Generacion automatica de PowerPoint (postergado para version 2)
- Sistema multiusuario local (reservado para version 2)
- Inferencia de modelos locales ONNX o llama.cpp (descartado por enfoque nube)

## 3. Desglose de Tareas

### 3.1 Infraestructura y Seguridad (Sprint 1)

| ID | Tarea | Prioridad | Est. (hrs) | Dependencias |
|----|-------|-----------|-------------|--------------|
| T-001 | Crear estructura de directorios y .gitignore estricto (incluyendo docs_internos/) | Alta | 1 | - |
| T-002 | Configurar entorno virtual y requirements.txt (PyQt6, Pydantic, keyring, langchain-openai) | Alta | 2 | T-001 |
| T-003 | Implementar gestor de configuracion segura (Keyring para OpenRouter API) | Alta | 3 | T-002 |

### 3.2 Logica Core y RAG (Sprint 1)

| ID | Tarea | Prioridad | Est. (hrs) | Dependencias |
|----|-------|-----------|-------------|--------------|
| T-101 | Implementar SQLite y Modelos Pydantic (Receta, Evento, AccionOffice) | Alta | 4 | T-001 |
| T-102 | Configurar LangChain Adapter para OpenRouter (MiniMax 2.7) | Alta | 5 | T-003 |
| T-103 | Implementar logica de recuperacion RAG hibrida simulada/SQLite | Media | 4 | T-101 |

### 3.3 Orquestacion asincrona y HITL (Sprint 2)

| ID | Tarea | Prioridad | Est. (hrs) | Dependencias |
|----|-------|-----------|-------------|--------------|
| T-201 | Implementar QThreadWorker con senales (streaming, error, accion_completada) | Alta | 6 | T-102 |
| T-202 | Implementar Maquina de Estados HITL (threading.Event.wait() / set()) | Alta | 5 | T-201 |
| T-203 | Implementar cliente adaptador para servidor MCP Office | Alta | 5 | T-101 |

### 3.4 Interfaz Grafica de Usuario - PyQt6 (Sprint 3)

| ID | Tarea | Prioridad | Est. (hrs) | Dependencias |
|----|-------|-----------|-------------|--------------|
| T-301 | Crear QMainWindow con QSplitter (Pantalla Dividida 40/60) | Alta | 5 | T-002 |
| T-302 | Implementar Modal de Boveda para API Keys (seguro con Keyring) | Alta | 2 | T-003, T-301 |
| T-303 | Conectar UI con QThread (Renderizar chat y previsualizacion) | Alta | 6 | T-201, T-301 |
| T-304 | Implementar Boton Flotante HITL y conexion de senal al evento | Alta | 3 | T-202, T-303 |

### 3.5 Pruebas y Empaquetado (Sprint 4)

| ID | Tarea | Prioridad | Est. (hrs) | Dependencias |
|----|-------|-----------|-------------|--------------|
| T-401 | Pruebas de integracion del flujo HITL con MCP Sandbox | Alta | 4 | T-304, T-203 |
| T-402 | Script de PyInstaller (--windowed) y creacion del .exe | Alta | 3 | Todas |

## 4. Cronograma Detallado (Textual)

**Semana 1 (Sprint 1)**: T-001, T-002, T-003, T-101, T-102, T-103.
*Hito*: El LLM responde en consola usando Keyring y contratos Pydantic. La estructura de carpetas y el archivo .gitignore estan creados y auditados. Los modelos de datos (Receta, Evento, AccionOffice) pasan validacion de tipos.

**Semana 2 (Sprint 2)**: T-201, T-202, T-203.
*Hito*: Los hilos asincronosestan controlados mediante QThread y threading.Event. El cliente MCP esta estructurado para conectarse al servidor. La maquina de estados HITL responde correctamente cuando se invoca una herramienta de escritura.

**Semana 3 (Sprint 3)**: T-301, T-302, T-303, T-304.
*Hito*: La interfaz de pantalla dividida es completamente funcional. El agente de IA solicita permiso en la interfaz de usuario antes de continuar con una accion de escritura. Los botones de aprobacion y rechazo operan correctamente en el Panel Derecho.

**Semana 4 (Sprint 4)**: T-401, T-402.
*Hito*: Las pruebas de integracion del flujo completo HITL demuestran que el documento se crea en C:\Temp\ChefChat_Sandbox\ unicamente despues de la aprobacion del usuario. El archivo .exe se genera sin errores y la aplicacion abre en Windows 10/11 sin bloquearse.

## 5. Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigacion |
|--------|--------------|---------|-------------|
| Latencia de la API de OpenRouter | Alta | Medio | Implementar streaming de tokens obligatorio en QThread (senal chunk_recibido). Si la latencia supera 5 segundos, mostrar indicador de carga en la interfaz. |
| El servidor MCP Office bloquea la GUI | Media | Alto | Asegurar que mcp_client se ejecute exclusivamente dentro del QThreadWorker y nunca en el hilo principal de Qt. Validar timeout en llamadas MCP. |
| Exposicion de la carpeta de Documentacion | Baja | Critico | Verificar auditoria del .gitignore en la T-001 antes de cualquier commit. Incluir verificacion automatica en pre-commit hook. |
| Falla de validacion Pydantic en acciones MCP | Media | Alto | El orquestador implementa reintento automatico (maximo 2 veces) con el mensaje re-formateado antes de mostrar error al usuario. |
| Credenciales invalidas en produccion | Baja | Alto | El modal de boveda permite re-ingreso de API Key sin necesidad de reiniciar la aplicacion. |

## 6. Criterios de Aceptacion del Proyecto (Verificables)

- La carpeta docs_internos/ y el archivo .env NO se suben al repositorio publicoy el .gitignore contiene las directivas correctas desde la T-001.
- La API Key de OpenRouter se almacena unicamente en el Keyring del sistema operativo y nunca en archivos de texto plano.
- La interfaz se abre en Windows 10/11 sin bloquearse y el QThread no congela la GUI durante llamadas de red.
- El flujo HITL funciona: cuando el agente detecta una accion de escritura MCP, el QThread se pausa, la UI muestra el dialogo de aprobacion y, al aceptar, el archivo se crea en C:\Temp\ChefChat_Sandbox\.
- El chat muestra streaming de tokens con latencia visible inferior a 1 segundo por chunk.
- Los contratos Pydantic validan correctamente Receta, Evento y AccionOffice sin errores de tipos.
- El cliente MCP opera exclusivamente dentro del entorno Sandbox, rechazando rutas externas.
- El archivo .exe generado por PyInstaller abre la aplicacion y responde a interacciones basicas del usuario.
- Los logs de telemetria no contienen PII ni claves de API.