# ChefChat Pro v1.0 — Manual de Usuario

## 1. Introduccion

ChefChat Pro es un asistente de escritorio con IA para la gestion integral de restaurantes. Emplea un sistema multiagente donde cada agente tiene su propio prompt de sistema especializado, usa el LLM seleccionado por el usuario, y responde exclusivamente con datos del sistema RAG local.

### Requisitos del Sistema

- **Sistema Operativo**: Windows 10/11 (64 bits)
- **Python**: 3.10 o superior
- **RAM**: 8 GB minimo (16 GB recomendado)
- **Disco**: 2 GB de espacio libre
- **Office**: Microsoft Word, Excel, PowerPoint 2016+ (para integracion COM)
- **Ollama** (opcional): Para uso de modelos locales gratuitos

## 2. Instalacion

### 2.1 Instalacion Rapida

```powershell
git clone <url-del-repositorio>
cd ChefChat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

### 2.2 Configuracion de Proveedores IA

Editar el archivo `.env` con los valores correspondientes:

```ini
# Proveedor principal (openrouter, deepseek, gemini, claude, openai, opencode, ollama)
CHEFCHAT_AI_PROVIDER=openrouter

# API Keys
CHEFCHAT_OPENROUTER_API_KEY=sk-or-v1-...
CHEFCHAT_DEEPSEEK_API_KEY=sk-...
CHEFCHAT_GEMINI_API_KEY=...
CHEFCHAT_CLAUDE_API_KEY=sk-ant-...
CHEFCHAT_OPENAI_API_KEY=sk-...

# Configuracion opcional
CHEFCHAT_DB_PATH=chefchat.db
CHEFCHAT_RAG_ONLY=true
CHEFCHAT_LOG_LEVEL=INFO
```

### 2.3 Inicio de la Aplicacion

```powershell
python main.py
```

## 3. Interfaz de Usuario

### 3.1 Ventana Principal

La interfaz se compone de:

- **Panel de Chat** (izquierdo): Burbujas HTML con temas claro/oscuro. Muestra el historial de conversacion con el asistente.
- **Panel HITL** (derecho): Panel de aprobacion humana para acciones criticas en Office (Word, Excel, PowerPoint).
- **Barra de Accion Superior**: Selector de proveedor/modelo, selector de agente, y botones de accion.

### 3.2 Selector de Proveedor y Modelo

Selecciona el proveedor de IA y el modelo a utilizar:

| Proveedor | Modelos Disponibles | Costo |
|-----------|-------------------|-------|
| OpenRouter | minimax-2.7b, openrouter/auto, gpt-4o, claude-3-5-sonnet | Variable |
| DeepSeek | deepseek-chat, deepseek-coder | Bajo |
| Gemini | gemini-2.0-flash-exp, gemini-2.0-flash, gemini-1.5-pro | Bajo |
| Claude | claude-3-5-sonnet, claude-3-opus, claude-3-haiku | Medio |
| OpenAI | gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo | Medio |
| OpenCode | big-pickle, open-code-v1, code-assistant | Gratis |
| Ollama | llama3.2, llama3.1, mistral, codellama, phi3, gemma2 | Gratis (local) |

### 3.3 Selector de Agente

Permite elegir un agente especifico o modo Automatico:

| Modo | Comportamiento |
|------|---------------|
| **Auto** | El orquestador detecta automaticamente la intencion y selecciona el agente adecuado |
| **Recetas** | Ejecuta consultas sobre el recetario del RAG |
| **Inventario** | Gestiona stock, caducidades, compras inteligentes |
| **Menu** | Planifica menus semanales, menu anti-desperdicio |
| **Mermas** | Registra y reporta desperdicios, sobrantes reutilizables |
| **Documentos** | Busca documentos RAG, gestiona personal |

### 3.4 Botones de Accion

| Boton | Funcion |
|-------|---------|
| `+` | Cargar documentos al RAG (PDF, DOCX, TXT, CSV, XLSX) |
| **Word** | Enviar ultima respuesta a Microsoft Word |
| **Excel** | Enviar datos tabulares a Microsoft Excel |
| **PowerPoint** | Enviar resumen a Microsoft PowerPoint |
| **Docs** | Generar documentacion profesional desde `resumen.md` |
| **Limpiar** | Limpiar el historial de chat |
| **Tema** | Alternar entre tema claro y oscuro |

### 3.5 Sidebar

| Elemento | Funcion |
|----------|---------|
| Chat | Muestra el historial de conversacion |
| Telemetria | Dashboard con metricas de uso (tokens, costo, solicitudes) |
| Config | Acceso a configuracion de API keys |
| Docs | Generacion de documentacion |
| Limpiar | Limpiar pantalla |

## 4. Comandos y Consultas

### 4.1 Recetas

```
busca receta Sopa de Tomate
PLF-050
encuentra recetas con pollo y arroz
escala receta SOP-021 para 50 personas
```

### 4.2 Inventario

```
verificar stock bajo
productos por caducar en 3 dias
registra compra: 3 kintales de harina, caduca 12-03-2027
que productos tengo en inventario?
```

### 4.3 Menu Semanal

```
configurar menu semanal
menu para hoy con pollo
agregar plato al menu del miercoles
consultar menu semanal
```

### 4.4 Mermas y Desperdicio

```
registra merma: 2kg de tomate, caduco
reporte de mermas de esta semana
dashboard de mermas a Excel
registra sobrante: 1kg arroz cocido, Juan, matutino
```

### 4.5 Personal

```
personal activo
personal ausente hoy
registrar trabajador: EMP001 Juan Perez Cocinero matutino 08:00 17:00
registrar ausencia: EMP001, reposo medico, 2026-01-15 a 2026-01-17
consultar turno de hoy
```

### 4.6 Documentos

```
busca documento sobre buenas practicas
busca documento capacitacion
protocolo de limpieza
```

### 4.7 Compras y Produccion

```
orden de compra para harina
genera orden de produccion para pan
costo real vs teorico del menu de hoy
```

### 4.8 Exportacion

```
exporta estos datos a Excel
a Word con formato
a PowerPoint con resumen
```

## 5. HITL (Human-in-the-Loop)

El sistema requiere aprobacion humana para acciones criticas en Microsoft Office:

1. El usuario solicita una exportacion a Word/Excel/PowerPoint
2. El sistema prepara los datos y muestra una vista previa en el panel derecho
3. El usuario revisa y hace clic en **Aprobar** o **Rechazar**
4. Solo tras la aprobacion se ejecuta la accion en Office

## 6. Telemetria

El dashboard de telemetria muestra:

- **Costo total USD**: Suma acumulada de todas las operaciones
- **Tokens totales**: Suma de tokens de entrada y salida
- **Solicitudes API**: Numero total de llamadas a la IA
- **Tabla de operaciones**: Ultimas 50 operaciones con detalle (modelo, tokens, costo, tipo)
- **Auto-refresh**: Cada 30 segundos
- **Exportacion**: CSV y JSON

## 7. Solucion de Problemas

### 7.1 Error de API Key

```
Error: Authentication failed
Solucion: Verificar que la API key este configurada en .env o en el keyring del sistema.
```

### 7.2 Error de Conexion con Ollama

```
Error: Connection refused
Solucion: Verificar que Ollama este instalado y ejecutandose (ollama serve).
Descargar modelo: ollama pull llama3.2
```

### 7.3 Error de Office

```
Error: COM object creation failed
Solucion: Verificar que Microsoft Office este instalado.
Ejecutar como Administrador si persiste el error.
```

### 7.4 Documento no Encontrado

```
Recipe not found in the system
Solucion: Usar el boton [+] para cargar documentos al RAG.
Formatos soportados: PDF, DOCX, TXT, CSV, XLSX.
```

## 8. Consejos de Uso

1. **Usar lenguaje natural**: El sistema entiende espanol coloquial ("se compro 3 kintales de harina")
2. **Especificar fechas**: Incluir fechas explicitas para registro de ausencias y compras
3. **Recetas por ID**: Usar codigos como PLF-050, SOP-021 para busqueda exacta
4. **Contexto automatico**: El sistema mantiene contexto de la conversacion
5. **RAG-only**: Por defecto, el LLM solo responde con datos existentes en el sistema
6. **Prompts en ingles**: Los prompts internos estan en ingles (~28% ahorro de tokens), las respuestas en espanol

## 9. Atajos de Teclado

| Atajo | Accion |
|-------|--------|
| Enter | Enviar mensaje |
| Ctrl+L | Limpiar chat |
| Ctrl+D | Generar documentacion |
| Ctrl+T | Cambiar tema |

---

*Documento generado para ChefChat Pro v1.0 — Mayo 2026*
