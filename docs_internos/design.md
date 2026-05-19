# Documento de Diseño Visual: ChefChat (AI Restaurant Assistant)

## 1. Resumen Ejecutivo

ChefChat implementa una interfaz de productividad de doble panel optimizada para Windows que maximiza la eficiencia del usuario en entornos profesionales de restauracion. El Panel Izquierdo (40%) concentra la comunicacion con el agente: historial de chat, entrada de texto y controles de configuracion. El Panel Derecho (60%) funciona como area de previsualizacion activa que cambia de contexto segun el tipo de operacion: muestra recetas RAG formateadas, documentos Word en borrador o tablas Excel pendientes de modificacion. El mecanismo HITL se materializa visualmente mediante un cambio de borde en naranja (Alerta HITL) y la aparicion de botones de aprobacion de tamano prominente, garantizando que el usuario sea consciente de cada accion critica antes de que el sistema escriba en archivos Office.

## 2. Privacidad de Documentación (Directiva de Empresa)

**CRITICO:** Todos los documentos de diseno, arquitectura y requisitos generados (requirements.md, architecture.md, design.md, etc.) son propiedad intelectual interna.
- **Regla visual/estructural:** Estos archivos deben residir en una carpeta docs_internos/ la cual DEBE estar incluida en el .gitignore del proyecto para evitar su publicacion en repositorios publicos.

## 3. Identidad Visual (Windows nativo)

### 3.1 Paleta de Colores

| Nombre | Codigo Hex | Uso |
|--------|------------|-----|
| Fondo Principal | #F3F3F3 | Panel de Chat |
| Fondo Visor | #FFFFFF | Panel de Documentos (Derecho) |
| Acento de Accion | #0078D7 | Botones primarios (Enviar) |
| Alerta HITL | #D83B01 | Borde del panel derecho cuando espera aprobacion |
| Exito | #107C10 | Confirmacion de documento guardado |
| Texto Primario | #323130 | Cuerpo de texto |
| Texto Secundario | #605E5C | Etiquetas y textos auxiliares |
| Borde Panel | #E1DFDD | Separadores y bordes sutiles |

### 3.2 Tipografia

| Elemento | Familia | Tamano | Peso |
|----------|---------|--------|------|
| Encabezado H1 | Segoe UI | 20px | Semibold (600) |
| Encabezado H2 | Segoe UI | 16px | Semibold (600) |
| Cuerpo de texto | Segoe UI | 14px | Regular (400) |
| Etiquetas | Segoe UI | 12px | Regular (400) |
| Entrada de texto | Segoe UI | 14px | Regular (400) |

### 3.3 Espaciado Base

Modulo base: 4px. Todos los espaciados使用的是 multiplos de 4 (8px, 12px, 16px, 24px, 32px).

## 4. Estructura de Navegacion y Pantalla Dividida (Split-Screen)

### 4.1 Layout General (Wireframe Textual)

**Resolucion Base**: 1200x800 pixeles (redimensionable).
**Estructura principal**: Un QSplitter divide la ventana verticalmente con divisor movil de 4px.

**Panel Izquierdo (40% - 480px ancho minimo)**:
- **Top (64px de altura)**:
  - Selector de modelo desplegable (opciones: MiniMax 2.7 via OpenRouter)
  - Boton de icono de candado para abrir modal de credenciales
- **Middle (area flex)**:
  - Area de scroll para historial de chat (burbujas de mensaje)
  - Burbuja de usuario alineada a la derecha
  - Burbuja de IA alineada a la izquierda
- **Bottom (80px de altura)**:
  - Campo de entrada de texto multilinea (QTextEdit, max 3 lineas visibles)
  - Boton Enviar con icono de flecha

**Panel Derecho (60% - 720px ancho minimo)**:
- **Top (48px de altura)**:
  - Titulo contextual que cambia segun estado (Idle / Receta / Documento Word / Excel)
- **Middle (area flex)**:
  - **Estado Inactivo**: Mensaje de bienvenida centrado con estadisticas de uso
  - **Estado RAG**: Tarjeta de receta formateada con secciones (Nombre, Ingredientes, Alergenos, Costo)
  - **Estado MCP Word**: Previsualizacion del documento en formato texto enriquecido
  - **Estado MCP Excel**: Tabla con datos del archivo abierta en modo solo lectura
- **Bottom (64px de altura, solo visible en estado HITL)**:
  - Barra flotante con borde naranja (Alerta HITL)
  - Boton [RECHAZAR] (estilo secundario, borde)
  - Boton [APROBAR CAMBIO] (estilo primario, fondo azul, mas grande)

## 5. Esquemas de Dialogos (Modales)

### 5.1 Bóveda de Credenciales (API Keys)

**Modal de 400x200 pixeles, centrado en pantalla principal.**
- **Encabezado**: Icono de candado + Titulo "Configuracion de Seguridad"
- **Cuerpo**:
  - Campo OpenRouter API Key (QLineEdit en modo password con boton de mostrar/ocultar)
  - Texto de advertencia静音: "Las llaves se guardaran en el administrador de credenciales de Windows (Keyring), no en archivos de texto."
- **Pie**: Boton [Cancelar] + Boton [Guardar en Bóveda] (primario)

### 5.2 Dialogo de Aprobacion HITL

**Panel modal de 500x300 pixeles que aparece sobre el Panel Derecho.**
- **Cuerpo**:
  - Mensaje: "El agente esta por ejecutar la siguiente accion:"
  - Descripcion de la accion en negrita (ej. "Crear documento menu_evento.docx")
  - Previsualizacion del contenido a escribir
- **Pie**:
  - Boton [Rechazar] (izquierda, estilo secundario)
  - Boton [Aprobar y Ejecutar] (derecha, estilo primario con icono de check)

## 6. Flujos de Usuario (Conductual)

### 6.1 Flujo Consulta RAG (Receta)

1. Usuario escribe en el campo de entrada: "Dame la receta del Pato a la Naranja"
2. Se habilita indicador de carga en el historial (dots animadas junto al ultimo mensaje)
3. Panel Derecho muestra indicador de busqueda (spinner)
4. IA responde en el chat con un resumen de una linea
5. Panel Derecho se actualiza automaticamente mostrando la ficha tecnica completa de la receta:
   - Nombre del plato (H1)
   - Lista de ingredientes (bullet points)
   - Seccion de alergenos resaltada en naranja
   - Costo estimado por porcion
6. Usuario puede hacer scroll en la receta y volver al chat

### 6.2 Flujo de Aprobacion MCP (HITL - Maquina de Estados)

1. Usuario escribe: "Crea el menu para el evento corporativo de manana en Word"
2. Burbuja de carga aparece en el chat
3. Agente Supervisor detecta intencion MCP y delega al Agente Word
4. Agente Word genera el boceto del documento
5. **Interrupcion (HITL)**:
   - QThread se pausa mediante event.wait()
   - Panel Derecho muestra el boceto del documento en previsualizacion
   - Borde del Panel Derecho cambia a color naranja (Alerta HITL #D83B01)
   - Barra flotante HITL aparece en la parte inferior del panel
6. Usuario revisa el contenido del menu en el panel derecho
7. Usuario hace clic en [APROBAR CAMBIO]
8. Barra flotante desaparece, boton se deshabilita brevemente
9. QThread se reanuda via event.set()
10. Accion MCP se ejecuta en Sandbox (C:\Temp\ChefChat_Sandbox\)
11. Panel Derecho muestra confirmacion de exito (mensaje verde con ruta del archivo)
12. Chat muestra mensaje del agente: "Documento guardado exitosamente en Sandbox"

## 7. Diseno Responsive

### 7.1 Comportamiento de Colapso

- Cuando el ancho de ventana es menor a 900px, el QSplitter fuerza el colapso del Panel Derecho
- El Panel Derecho se convierte en una pestana inferior (QTabWidget) con dos paginas:
  - Pestana 1: "Chat" (_panel izquierdo visible)
  - Pestana 2: "Visor / Aprobaciones" (panel derecho completo)
- El usuario alterna manualmente entre las pestanas
- Indicador visual (badge) aparece en la pestana "Aprobaciones" cuando hay una accion HITL pendiente

### 7.2 Altura Minima

Altura minima de ventana: 600px. Por debajo de este valor, la ventana muestra un mensaje de "Redimensione la ventana para continuar".

## 8. Siguientes Pasos

El Agente 4 (Diseno Tecnico Detallado) tomara esta estructura visual y definira los Layouts de PyQt6 (QHBoxLayout, QSplitter) y la conexion de la senal de los botones HITL con el evento de la Maquina de Estados.