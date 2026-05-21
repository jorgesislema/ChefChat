# ChefChat Pro v1.0 — Seguridad y Control de Calidad

## 1. Modelo de Seguridad

### 1.1 Principios de Seguridad

1. **Zero credenciales en codigo fuente**: Las API keys nunca se almacenan en archivos de codigo
2. **Defensa en profundidad**: Multiples capas de validacion (input, contenido, rate limiting)
3. **Menor privilegio**: El sistema solo accede a los recursos necesarios
4. **Sandboxing**: Operaciones de Office limitadas a directorio controlado
5. **Validacion estricta**: Contratos Pydantic con `extra = "forbid"` en herramientas

### 1.2 Arquitectura de Seguridad

```
                    ┌─────────────────────────────┐
                    │     Capa de Presentacion     │
                    │  (GUI - PyQt6)               │
                    └─────────────┬───────────────┘
                                  │
                    ┌─────────────▼───────────────┐
                    │   Capa de Validacion (Ops)   │
                    │  ┌───────────────────────┐  │
                    │  │   Guardrails           │  │
                    │  │  - InputValidator      │  │
                    │  │  - InjectionDetector   │  │
                    │  │  - ContentFilter       │  │
                    │  │  - RateLimiter         │  │
                    │  └───────────────────────┘  │
                    └─────────────┬───────────────┘
                                  │
                    ┌─────────────▼───────────────┐
                    │   Capa de Negocio            │
                    │  - Orchestrator              │
                    │  - Multi-Agent System        │
                    └─────────────┬───────────────┘
                                  │
                    ┌─────────────▼───────────────┐
                    │   Capa de Datos              │
                    │  - DB Manager                │
                    │  - RAG Store                 │
                    │  - Semantic RAG              │
                    └─────────────────────────────┘
```

## 2. Guardrails (Proteccion contra Inyeccion)

### 2.1 PromptInjectionDetector

**23 patrones de inyeccion detectados**:

| Categoria | Patrones | Ejemplo |
|-----------|----------|---------|
| Ignorar instrucciones | 5 | "ignore las instrucciones anteriores" |
| Modo DAN/Jailbreak | 4 | "actua como DAN", "sin restricciones" |
| Redireccion | 3 | "responde en otro idioma" |
| Suplantacion | 3 | "eres un asistente malvado" |
| Sobreescritura | 4 | "sobreescribe tu programacion" |
| Escape de contexto | 4 | "olvida todo lo anterior" |

**16 patrones sospechosos**:

| Categoria | Patrones | Ejemplo |
|-----------|----------|---------|
| Codigo | 4 | "ejecuta codigo", "os.system" |
| Extraccion | 4 | "dame tu prompt", "repeat after me" |
| Encoding | 4 | "encode in base64", "decode" |
| Acceso a archivos | 4 | "lee el archivo", "cat /etc/" |

### 2.2 InputValidator

| Regla | Valor | Accion |
|-------|-------|--------|
| Longitud maxima | 5000 caracteres | Bloquear y notificar |
| Maximo palabras | 500 palabras | Bloquear y notificar |
| Whitespace | Trim automático | Corregir |
| Caracteres nulos | Rechazar | Bloquear |

### 2.3 ContentFilter

| Elemento Bloqueado | Patron |
|--------------------|--------|
| URLs | http://, https:// |
| Direcciones IP | \d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3} |
| Rutas de archivo | [A-Za-z]:\\, /etc/, /usr/ |
| Comandos shell | exec, system, popen, subprocess |

### 2.4 RateLimiter

| Parametro | Valor por Defecto | Configurable |
|-----------|------------------|--------------|
| Max requests | 5 | Si (max_requests) |
| Ventana de tiempo | 60 segundos | Si (window_seconds) |
| Algoritmo | Sliding window | Fijo |

### 2.5 Niveles de Amenaza

| Nivel | Sigilo | Accion |
|-------|--------|--------|
| SAFE | 0 | Permitir paso |
| SUSPICIOUS | 1-5 | Registrar alerta, permitir paso |
| BLOCKED | > 5 | Bloquear, registrar, notificar usuario |

## 3. Gestion de API Keys

### 3.1 Almacenamiento Seguro

```
┌─────────────────────────────┐
│  Orden de Resolucion        │
│                             │
│  1. Variable de entorno     │
│     (CHEFCHAT_*_API_KEY)    │
│                             │
│  2. Keyring del SO          │
│     (Servicio: ChefChat)    │
│                             │
│  3. Dialogo GUI             │
│     (Solo en memoria)       │
└─────────────────────────────┘
```

### 3.2 Variables de Entorno Soportadas

```ini
CHEFCHAT_OPENROUTER_API_KEY=sk-or-v1-...
CHEFCHAT_DEEPSEEK_API_KEY=sk-...
CHEFCHAT_GEMINI_API_KEY=...
CHEFCHAT_CLAUDE_API_KEY=sk-ant-...
CHEFCHAT_OPENAI_API_KEY=sk-...
CHEFCHAT_OPENCODE_API_KEY=...
CHEFCHAT_OLLAMA_API_KEY= (opcional)
```

### 3.3 Redaccion en Logs

El sistema redacta automaticamente API keys y tokens en los logs:
- `sk-*` → `[REDACTED]`
- `ghp_*` → `[REDACTED]`
- Bearer tokens → `[REDACTED]`
- Correos electronicos → `[REDACTED]`

## 4. Sandbox de Office

### 4.1 Directorio Sandbox

Todas las operaciones de Office se limitan a:
```
C:\Temp\ChefChat_Sandbox\
```

Configurable via: `CHEFCHAT_SANDBOX_PATH` en `.env`

### 4.2 Validaciones de Seguridad

- Path traversal prevention
- Extensiones permitidas: .docx, .xlsx, .pptx
- No se permite ejecucion de macros
- Tiempo maximo de operacion: 60 segundos

## 5. Control de Calidad

### 5.1 Suite de Pruebas

```
python -m pytest tests/ -v
```

**Resultados actuales**: 79 pruebas pasan, 3 skipped, 2 errors

### 5.2 Cobertura por Modulo

| Modulo | Pruebas | Cobertura |
|--------|---------|-----------|
| Guardrails | 10 pruebas | Deteccion de inyeccion, validacion |
| Ollama Provider | 4 pruebas | Conexion y respuesta |
| DSPy Optimizer | 8 pruebas | Optimizacion y expansion |
| Multiagent System | 13 pruebas | Routing, ejecucion, integracion |
| GUI | 13 pruebas | Interfaz y eventos |
| MCP Client | 6 pruebas | Office integration |
| Modelos Pydantic | 12 pruebas | Validacion de datos |
| Worker | 5 pruebas | HITL y threading |

### 5.3 Pruebas de Integracion

Las pruebas de integracion verifican:
- Flujo completo: GUI → Worker → Orchestrator → Agente → Respuesta
- Integracion MCP con Office (simulada)
- Pipeline RAG completo

### 5.4 Escaneo de Seguridad

Ejecutar periodicamente:
```bash
python scripts/security_scan.py
```

Este script escanea:
- 40+ patrones de API keys y tokens
- Credenciales hardcodeadas
- Archivos de configuracion expuestos
- Secretos en codigo fuente

### 5.5 Verificacion del Sistema

```bash
python scripts/check_setup.py
```

Verifica:
- Dependencias de Python instaladas
- API keys configuradas
- Base de datos accesible
- Permisos de archivos
- Conectividad con proveedores IA

## 6. HITL (Human-in-the-Loop)

### 6.1 Acciones que Requieren Aprobacion

| Accion | Riesgo | Justificacion |
|--------|--------|---------------|
| Exportar a Word | Medio | Modificacion de documentos |
| Exportar a Excel | Medio | Modificacion de datos financieros |
| Exportar a PowerPoint | Medio | Presentaciones oficiales |

### 6.2 Flujo HITL

```
1. Usuario solicita exportacion
2. Sistema prepara datos
3. Muestra preview en panel derecho
4. Usuario revisa contenido
5. Usuario hace clic en Aprobar/Rechazar
6. Solo si se aprueba: ejecutar accion en Office
7. Timeout: 60 segundos (se rechaza automaticamente)
```

## 7. Plan de Continuidad

### 7.1 Degradacion Graceful

| Falla | Comportamiento |
|-------|---------------|
| API key invalida | Notificar al usuario, ofrecer cambiar proveedor |
| BD corrupta | Crear BD nueva, notificar perdida de datos |
| Office no disponible | Usar fallback openpyxl/matplotlib |
| Ollama no responde | Notificar, sugerir instalar o cambiar proveedor |
| RAG sin documentos | Notificar, sugerir cargar documentos |

### 7.2 Backup y Recuperacion

| Recurso | Metodo de Backup | Frecuencia |
|---------|-----------------|------------|
| Base de datos | Copiar chefchat.db | Diario |
| Documentos RAG | Backup de data_source/ | Semanal |
| Configuracion | Backup de .env | Al cambiar |
| Telemetria | Exportar dashboard CSV | Semanal |

---

*Documento generado para ChefChat Pro v1.0 — Mayo 2026*
