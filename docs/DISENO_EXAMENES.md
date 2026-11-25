# Diseño del módulo de exámenes (ChefChat)

Estado: diseño, sin código. Falta confirmar los puntos marcados con **[CONFIRMAR]**.

## 1. Para qué sirve
El dueño capacita a su personal con los manuales cargados (BPM, alérgenos, atención al cliente) y mide si aprendieron.

| Modo | Para qué | Reglas |
|---|---|---|
| Práctica | Aprender | Sin límite de tiempo. Muestra si acertó y la explicación al instante. No cuenta para nota. |
| Evaluación | Medir | Tiempo límite. Sin pistas. Nota al final. Se guarda en el historial. 2 intentos por persona (configurable). |

## 2. Flujo paso a paso
1. El trabajador entra, elige su nombre (tabla `Trabajadores`) y el tema (un manual).
2. Elige **Práctica** o **Evaluación**.
3. El sistema arma 10 preguntas del banco aprobado de ese tema, en orden mezclado.
4. Se muestra una pregunta a la vez, con barra de avance (3/10).
5. Práctica: tras responder, muestra ✔/✘, la respuesta correcta y la fuente ("Buenas Prácticas (BPM), Sección 1.2").
6. Evaluación: sin feedback hasta el final.
7. Al terminar: nota, aprobado/no aprobado, preguntas falladas con su fuente.
8. El dueño ve en el panel: quién aprobó, quién no, y los temas más fallados.

## 3. Cómo nacen las preguntas (sin inventar)
1. Para cada fragmento de `ChunksDoc` (RAG de documentos), la IA propone 1 a 3 preguntas **solo con ese texto**.
2. Cada pregunta guarda `documento` y `seccion` de origen.
3. **JEV (modelo juez)** puntúa cada pregunta (ver sección 6).
4. Las preguntas con puntaje alto pasan a la bandeja del dueño. **Nada entra al banco sin su aprobación** (HITL).
5. Si cambia el manual, las preguntas de ese fragmento pasan a "revisar".

## 4. Tipos de pregunta
- Opción múltiple (4 opciones, 1 correcta). Principal.
- Verdadero / Falso.
- Respuesta corta: se califica por palabras clave obligatorias (definidas al aprobar la pregunta). Sin IA para calificar, para que sea justo y repetible.

## 5. Datos (tablas nuevas en `chefchat.db`)
| Tabla | Campos clave |
|---|---|
| `PreguntasExamen` | id, tema, tipo, enunciado, opciones(json), correcta, explicacion, documento, seccion, puntaje_jev, estado(`pendiente`/`aprobada`/`revisar`/`retirada`) |
| `Examenes` | id, tema, modo, n_preguntas, minutos, nota_minima |
| `Intentos` | id, id_empleado, examen_id, inicio, fin, nota, aprobado |
| `Respuestas` | intento_id, pregunta_id, elegida, correcta(0/1), segundos |

## 6. JEV (modelo juez)
Interfaz conocida: se envía `model`, `state` y `questions`; devuelve una **probabilidad por pregunta**.

Ejemplo de uso previsto (forma exacta **[CONFIRMAR]**: URL, nombre de campos y qué significa la probabilidad):
```json
{ "model": "jev", "state": "validar_pregunta",
  "questions": [ {"id": "Q12", "enunciado": "...", "correcta": "B", "fuente": "texto del fragmento"} ] }
```
Respuesta esperada: `{"Q12": 0.93}`.

Uso propuesto: probabilidad de que la pregunta sea **correcta y respondible con su fuente**.
- ≥ 0,80: va a la bandeja del dueño.
- 0,50 a 0,79: va marcada "dudosa".
- < 0,50: se descarta.

## 7. Funciones (entradas y salidas)
| Función | Entra | Sale |
|---|---|---|
| `generar_preguntas(tema)` | tema | lista de preguntas `pendiente` |
| `puntuar_con_jev(preguntas)` | preguntas | `{id: probabilidad}` |
| `aprobar_pregunta(id, editado)` | id, texto editado | pregunta `aprobada` |
| `armar_examen(tema, modo, n)` | tema, modo, n | `examen_id` + preguntas mezcladas |
| `iniciar_intento(id_empleado, examen_id)` | empleado, examen | `intento_id` o error "sin intentos" |
| `responder(intento_id, pregunta_id, elegida)` | ids, opción | `{correcta, explicacion, fuente}` solo en práctica |
| `cerrar_intento(intento_id)` | intento | `{nota, aprobado, falladas[]}` |
| `reporte_dueno(desde, hasta)` | fechas | tabla por persona y tema |

## 8. Mensajes fijos
- Inicio evaluación: "Tienes {min} minutos y {n} preguntas. No podrás volver atrás. ¿Empezamos?"
- Aprobado: "¡Aprobaste con {nota}! Buen trabajo."
- No aprobado: "Sacaste {nota}. Necesitas {minimo}. Repasa estas secciones y vuelve a intentarlo."
- Sin intentos: "Ya usaste tus {n} intentos. Habla con tu encargado."
- Tema sin preguntas: "Este tema aún no tiene preguntas aprobadas."

## 9. Pantallas
1. Inicio del trabajador: nombre, tema, modo.
2. Pregunta: enunciado grande, opciones como tarjetas, barra de avance, reloj (solo evaluación).
3. Resultado: nota en grande, falladas con fuente.
4. Panel del dueño: bandeja de preguntas por aprobar, resultados por persona, temas más fallados.

## 10. Pruebas
- Cada pregunta del banco aprobado tiene fuente que existe en `ChunksDoc` (prueba automática).
- La nota se calcula igual en 10 casos de ejemplo conocidos.
- Un empleado no puede pasar de sus intentos.
- Práctica no escribe en el historial de evaluación.
- Datos de prueba ficticios.

## 11. Etapas
1. Confirmar JEV (URL, campos, significado).
2. Tablas + generación + bandeja de aprobación.
3. Práctica.
4. Evaluación + reporte del dueño.
5. Pantalla web final (junto con el rediseño).
