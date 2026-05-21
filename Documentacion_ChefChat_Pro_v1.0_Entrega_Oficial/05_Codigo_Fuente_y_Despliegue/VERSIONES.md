# ChefChat Pro v1.0 — Registro de Versiones

## v1.0.0 (Mayo 2026)

### Nuevas Funcionalidades

**Sistema Multiagente**
- 5 agentes especializados con prompts individuales en ingles (~28% ahorro de tokens)
- Planner + Executor para tareas complejas
- Routing inteligente con 9 niveles de prioridad
- Alertas cruzadas entre agentes

**Proveedores de IA**
- OpenRouter (principal)
- DeepSeek
- Gemini
- Claude
- OpenAI
- OpenCode (gratuito)
- Ollama (local, gratuito)

**Seguridad**
- Guardrails: 23 patrones de deteccion de inyeccion
- Rate limiting con sliding window
- Filtro de contenido (URLs, IPs, comandos shell)
- Sandbox para operaciones de Office
- HITL (Human-in-the-Loop) para acciones criticas

**RAG (Retrieval-Augmented Generation)**
- Clasificador automatico de documentos
- Busqueda por keywords y semantica (FAISS)
- Duplicados detectados al cargar
- Expansion de consultas con sinonimos culinarios

**Integracion con Office**
- Exportacion a Word, Excel, PowerPoint via COM
- Plantillas con variables {{variable}}
- Dashboard fallback con openpyxl/matplotlib
- Sandbox path validation

**GUI**
- Interfaz PyQt6 con tema claro/oscuro
- Panel de chat con burbujas HTML
- Dashboard de telemetria con KPI cards
- Selector de agente (Auto/especifico)
- Document upload (+)

**Base de Datos**
- 15+ tablas SQLite
- Catalogo, Inventario, Recetas, Mermas, Personal
- Menu semanal (7 dias x 4 servicios)
- Telemetria con metricas de rendimiento

**Optimizacion DSPy**
- Few-shot examples
- Expansion de consultas
- Feedback de relevancia

### Pruebas
- 79 pruebas pasan
- 3 pruebas skipped (requieren Ollama instalado)
- 2 errores (aislamiento Qt en ejecucion masiva)

### Compatibilidad
- Windows 10/11
- Python 3.10+
- Microsoft Office 2016+

### Limitaciones Conocidas

1. **RAG**: Busqueda principal usa SQLite LIKE; busqueda semantica FAISS requiere `sentence-transformers`
2. **HITL**: Timeout de 60 segundos para aprobacion
3. **Office**: Requiere COM, no disponible en Linux/Mac
4. **Ollama**: Requiere instalacion separada de Ollama
5. **Qt**: Pruebas GUI requieren aislamiento de QApplication

---

*Documento generado para ChefChat Pro v1.0 — Mayo 2026*
