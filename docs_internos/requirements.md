# Documento de Requisitos: ChefChat (AI Restaurant Assistant)

## 1. Resumen Ejecutivo

ChefChat es un asistente de IA de escritorio para gestion de restaurantes, dirigido a Chefs y Administradores. Utiliza PyQt6 para la interfaz en Windows, OpenRouter con modelo MiniMax 2.7 para inferencia en la nube, y RAG hibrido para consulta de recetas y manuales BPM. El sistema orquesta agentes especializados: un Agente Supervisor para clasificacion de intenciones, un Agente RAG para recuperacion de documentos, y un Agente MCP para automatizacion de Microsoft Office (Word/Excel) con aprobacion humana (HITL). Toda la seguridad de credenciales se gestiona mediante Keyring del sistema operativo, sin armazenar claves en codigo.

## 2. Stakeholders y Usuarios

| Rol | Descripcion | Intereses |
|-----|-------------|-----------|
| Administrador / Gerente | Gestiona costos y eventos | Precision en Excel, reportes rapidos, control de aprobaciones |
| Chef / Personal de Cocina | Consulta recetas y BPM | Respuestas exactas (RAG), cero alucinaciones en alergenos |

## 3. Requisitos Funcionales (RF)

### 3.1 Gestion de Conversacion y Orquestacion

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-01 | El sistema debe clasificar la intencion del usuario (Consulta RAG vs. Accion MCP) | Alta |
| RF-02 | El sistema debe mantener el contexto de la conversacion (Memoria en SQLite) | Alta |

### 3.2 Integracion IA en la Nube y RAG Hibrido

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-IA-01 | El sistema debe conectarse a OpenRouter (modelo MiniMax 2.7) para inferencia | Alta |
| RF-IA-02 | Implementar RAG hibrido (Semantico + Keyword) para indexar Recetas y manuales BPM | Alta |
| RF-IA-03 | Las extracciones de datos (Recetas, Eventos) deben estar tipadas mediante contratos Pydantic | Alta |

### 3.3 Interfaz Grafica (PyQt6 - Escritorio Windows)

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-UI-01 | Diseno de pantalla dividida: Chat a la izquierda, Visor/Controles a la derecha | Alta |
| RF-UI-02 | Selector de modelos e ingreso seguro de API Keys en la GUI (almacenamiento en Keyring) | Alta |
| RF-UI-03 | Mecanismo HITL: Boton de Aprobar/Rechazar en la UI que controle la pausa del QThread | Alta |

### 3.4 Conectividad MCP (Microsoft Office)

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-MCP-01 | El sistema debe usar un cliente MCP para leer/escribir en archivos Excel (costos/inventarios) | Alta |
| RF-MCP-02 | El sistema debe usar un cliente MCP para generar documentos Word (minutas, invitaciones) | Alta |
| RF-MCP-03 | Toda accion de escritura del MCP requiere aprobacion previa del usuario (HITL) | Alta |

## 4. Requisitos No Funcionales (RNF)

### 4.1 Rendimiento y Arquitectura

| ID | Requisito | Metrica |
|----|-----------|---------|
| RNF-01 | La GUI no debe congelarse durante llamadas de red o acciones MCP | Uso estricto de QThread |
| RNF-02 | Implementar streaming de tokens en la interfaz de chat | Latencia visible menor a 1 segundo |

### 4.2 Seguridad y Privacidad (Grado Repositorio Publico)

| ID | Requisito |
|----|-----------|
| RNF-03 | CERO CREDENCIALES EN CODIGO. Las API keys (OpenRouter, LangSmith) se gestionan con la libreria keyring del OS |
| RNF-04 | Las operaciones MCP deben ejecutarse en un entorno Sandbox (ej. C:\Temp\ChefChat_Sandbox) durante el desarrollo |
| RNF-05 | Los logs de telemetria no deben contener PII (Informacion Personal Identificable) ni claves |

### 4.3 Usabilidad y Mantenibilidad

| ID | Requisito |
|----|-----------|
| RNF-06 | La aplicacion sera empaquetada como .exe mediante PyInstaller |
| RNF-07 | Estructura modular (Clean Architecture) con contratos claros |

## 5. Requisitos de Datos

| Entidad | Formato Esperado (Pydantic) | Almacenamiento |
|--------|---------|-----------------|
| Receta | JSON (nombre, ingredientes, alergenos, costo) | Vector DB / SQLite |
| Evento | JSON (fecha, aforo, tipo, presupuesto) | SQLite |
| Manual BPM | Texto fragmentado (Chunking semantico) | Vector DB |

## 6. Restricciones Tecnicas

- Lenguaje: Python 3.10+
- Librerias Principales: PyQt6, Pydantic, LangChain/LlamaIndex, keyring
- Modelos: Inferencia via OpenRouter API. Embeddings via nube (Gemini/OpenAI) u Open Source ligero si el hardware lo permite
- Base de datos local: SQLite

## 7. Priorizacion MVP

| Incluir en MVP (V1) | Postergar para version 2 |
|----------------|--------------------------|
| Chat UI con streaming y selector de modelos | DSPy dinamico en produccion (solo offline en MVP) |
| RAG basico para Recetas | Generacion de PowerPoint via MCP |
| MCP para Word y Excel (con HITL) | Base de datos en la nube |
| Keyring para seguridad de API Keys | Sistema multi-usuario local |

## 8. Criterios de Aceptacion (Verificables)

- La GUI se abre en Windows 10/11 sin bloquearse
- El usuario ingresa una API Key en la UI, se guarda en Keyring y el chat responde usando OpenRouter
- El sistema recupera una receta correcta usando RAG y la muestra en formato estructurado
- El agente intenta modificar un Excel; el QThread se pausa, la UI muestra un dialogo de aprobacion y, al aceptar, se ejecuta el cambio en la carpeta Sandbox
- El repositorio en GitHub no contiene archivos .env con claves reales ni logs sensibles