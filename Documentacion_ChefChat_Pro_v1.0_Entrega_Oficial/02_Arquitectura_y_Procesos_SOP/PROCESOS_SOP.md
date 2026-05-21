# ChefChat Pro v1.0 — Procedimientos Operativos Estandar (SOP)

## 1. SOP-001: Inicio del Sistema

**Propósito**: Iniciar correctamente ChefChat Pro.

**Procedimiento**:
1. Activar entorno virtual: `.venv\Scripts\activate`
2. Verificar variables de entorno: `python scripts/check_setup.py`
3. Iniciar aplicacion: `python main.py`
4. Verificar que la ventana principal se muestre correctamente
5. Confirmar que el proveedor de IA este configurado

**Criterios de Aceptacion**:
- Ventana principal visible sin errores
- Selector de proveedor con opciones disponibles
- Chat listo para recibir consultas

## 2. SOP-002: Configuracion de Proveedor IA

**Propósito**: Configurar el proveedor de inteligencia artificial.

**Procedimiento**:
1. Hacer clic en el icono de configuracion (llave) en la barra lateral
2. Ingresar API key para el proveedor deseado
3. Seleccionar el proveedor en el dropdown superior
4. Seleccionar el modelo especifico
5. Enviar un mensaje de prueba

**Proveedores Soportados**:
- OpenRouter (recomendado)
- DeepSeek
- Gemini
- Claude
- OpenAI
- OpenCode (gratuito)
- Ollama (local, gratuito)

## 3. SOP-003: Carga de Documentos al RAG

**Propósito**: Cargar documentos al sistema RAG para consultas.

**Procedimiento**:
1. Hacer clic en el boton `[+]` en la barra de accion
2. Seleccionar uno o varios archivos (PDF, DOCX, TXT, CSV, XLSX)
3. El sistema clasifica automaticamente el tipo de documento
4. Confirmar la carga exitosa en el chat
5. Verificar con: "busca documento [nombre]"

**Formatos Soportados**:
| Formato | Tamano Maximo | Clasificacion Automatica |
|---------|---------------|-------------------------|
| PDF | 50 MB | Por contenido y nombre |
| DOCX | 50 MB | Por contenido y nombre |
| TXT | 10 MB | Por contenido y nombre |
| CSV | 50 MB | Por columnas y nombre |
| XLSX | 50 MB | Por columnas y nombre |

**Tipos Detectables**: receta, catalogo, lotes, manual_bpm, generico

## 4. SOP-004: Gestion de Recetas

**Propósito**: Buscar, escalar y gestionar recetas en el sistema.

**Procedimiento**:
1. **Busqueda por nombre**: "busca receta [nombre]"
2. **Busqueda por ID**: "[codigo]" (ej: PLF-050, SOP-021)
3. **Busqueda por ingredientes**: "recetas con [ingrediente] y [ingrediente]"
4. **Escalado**: "escala receta [ID] para [N] personas"
5. **Exportacion**: enviar receta a Word/Excel

**Codigos de Receta**:
| Prefijo | Tipo |
|---------|------|
| PLF | Plato fuerte |
| SOP | Sopa |
| BEB | Bebida |
| ENS | Ensalada |
| POS | Postre |
| ENT | Entrada |
| EVT | Evento especial |

## 5. SOP-005: Gestion de Inventario

**Propósito**: Controlar el inventario de productos.

**Procedimiento**:
1. **Verificar stock**: "verificar stock bajo"
2. **Productos por caducar**: "productos por caducar en [N] dias"
3. **Registrar compra**: "registra compra: [cantidad] de [producto]"
4. **Consultar inventario**: "que productos tengo en inventario?"
5. **Exportar reporte**: enviar reporte a Excel

## 6. SOP-006: Planificacion de Menu Semanal

**Propósito**: Configurar el menu semanal del restaurante.

**Procedimiento**:
1. **Configurar menu**: "configurar menu semanal"
2. **Agregar plato**: "agregar [plato] al menu del [dia]"
3. **Menu anti-desperdicio**: "menu anti desperdicio"
4. **Consultar menu**: "consultar menu semanal"
5. **Exportar menu**: enviar menu a Excel

**Estructura del Menu**:
| Dia | Desayuno | Almuerzo | Cena | Servicio Especial |
|-----|----------|----------|------|-------------------|
| Lunes | Plato 1 | Plato 2 | Plato 3 | Plato 4 |
| Martes | ... | ... | ... | ... |
| ... | ... | ... | ... | ... |

## 7. SOP-007: Registro de Mermas

**Propósito**: Registrar y reportar desperdicios.

**Procedimiento**:
1. **Registrar merma**: "registra merma: [cantidad] de [producto], [motivo]"
2. **Registrar sobrante**: "registra sobrante: [cantidad] [producto], [empleado], [turno]"
3. **Reporte**: "reporte de mermas de [periodo]"
4. **Dashboard**: "dashboard de mermas a Excel"
5. **Analisis**: "analizar rentabilidad del menu"

## 8. SOP-008: Gestion de Personal

**Propósito**: Gestionar el personal del restaurante.

**Procedimiento**:
1. **Registrar trabajador**: "registrar trabajador: [ID] [nombre] [cargo] [turno] [entrada] [salida]"
2. **Consultar personal activo**: "personal activo"
3. **Personal ausente**: "personal ausente hoy"
4. **Registrar ausencia**: "registrar ausencia: [ID], [motivo], [fecha_inicio] a [fecha_fin]"
5. **Registrar permiso**: "registrar permiso rapido: [ID]"

## 9. SOP-009: Exportacion a Microsoft Office

**Propósito**: Exportar datos a Word, Excel o PowerPoint.

**Procedimiento**:
1. **Generar datos**: Realizar consulta que genere datos tabulares
2. **Exportar**: "a [Word/Excel/PowerPoint]"
3. **Aprobar HITL**: Revisar y aprobar en panel HITL
4. **Verificar**: Confirmar que el documento se genero correctamente

**Reglas HITL**:
| Accion | Requiere HITL | Tiempo Maximo |
|--------|---------------|---------------|
| Exportar a Word | Si | 60 segundos |
| Exportar a Excel | Si | 60 segundos |
| Exportar a PowerPoint | Si | 60 segundos |
| Consulta simple | No | N/A |

## 10. SOP-010: Backup y Mantenimiento

**Propósito**: Realizar copias de seguridad del sistema.

**Procedimiento**:
1. **Backup de BD**: Copiar `chefchat.db` a ubicacion segura
2. **Exportar telemetria**: Usar dashboard de telemetria > exportar CSV/JSON
3. **Verificar integridad**: `python scripts/check_setup.py`
4. **Escaneo de seguridad**: `python scripts/security_scan.py`

**Frecuencia Recomendada**:
| Accion | Frecuencia |
|--------|------------|
| Backup BD | Diario |
| Exportar telemetria | Semanal |
| Verificar integridad | Semanal |
| Escaneo seguridad | Mensual |

## 11. SOP-011: Resolucion de Errores

**Propósito**: Diagnosticar y resolver errores comunes.

**Procedimiento**:
1. **Error de API**: Verificar conexion a internet y API keys
2. **Error de BD**: `python scripts/check_setup.py` para diagnostico
3. **Error de Office**: Verificar que Office este instalado y activado
4. **Error de Ollama**: `ollama serve` y `ollama list`
5. **Error de RAG**: Recargar documentos con boton `[+]`

---

*Documento generado para ChefChat Pro v1.0 — Mayo 2026*
