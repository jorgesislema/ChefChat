# Plan: balance del turno (kilos y unidades)

Fecha: 25 nov 2026. Estado: aprobado para construir.

## 1. El problema

El turno reporta lo que produjo y la merma que pesó. Lo que se pega a las máquinas, se cae, se sirve de más o se come
el personal **no se anota**. Esa pérdida se acumula sin verse y aparece años después como un hueco de miles.

Causa de fondo: **la misma persona que produce es la que anota**, nadie pesa lo que entra al turno y los números se
miran una vez al año.

## 2. La idea: balance de masas por turno

No se intenta pesar cada migaja. La pérdida invisible se **calcula por diferencia**:

```
lo que entró  =  lo bueno que salió  +  pérdida normal  +  lo que se anotó  +  SIN EXPLICAR
```

| Parte | De dónde sale | Quién lo anota |
|---|---|---|
| Lo que entró | entregas de bodega al turno, menos lo que se devolvió | **bodega** (no el turno) |
| Lo bueno que salió | unidades producidas × peso de cada una | el turno; lo **cuenta otra persona** al recibir |
| Pérdida normal | % estándar de cada receta (evaporación, lo que se pega), medido en pruebas | el dueño / jefe de producción |
| Lo que se anotó | merma pesada del turno + comida del personal + residuo de limpieza + muestras | el turno |
| **Sin explicar** | la resta | **nadie: lo calcula el sistema** |

### Ejemplo (panadería)

| Concepto | kg |
|---|---|
| Entregado por bodega | 600 |
| Devuelto a bodega | −5 |
| **Entró** | **595** |
| Salió bueno: 9 600 panes × 60 g | 576 |
| Pérdida normal (2,5 % de lo que debió entrar) | 14,8 |
| Merma pesada | 10 |
| Comida del personal | 2 |
| **Sin explicar** | **−7,8** → falta: el turno debió tener 7,8 kg más (1,3 %) |

Si el sin explicar pasa la **tolerancia** (por ejemplo 2 %), el turno queda en **alarma** ese mismo día.

## 3. Tres miradas del mismo balance

1. **Total en kilos** (la del ejemplo).
2. **Por ingrediente** (dónde está la fuga): para cada ingrediente,
   `entregado − devuelto − uso según receta − merma de ese ingrediente = diferencia`.
   El «uso según receta» = unidades producidas × cantidad del ingrediente en la receta (ya está en `RecetaIngredientes`).
   Ejemplo: se entregaron 50 kg de harina, las recetas usan 46 kg, merma 1 kg → faltan 3 kg de harina.
3. **Por unidades** (separación de funciones): para cada plato, `producido (lo dice el turno)` contra
   `recibido (lo cuenta otra persona: mostrador, despacho o salón)` y `vendido`.
   `producido − recibido` = unidades que se perdieron entre la cocina y la venta (se comieron, se cayeron, se regalaron).

## 4. Reglas de cálculo

- Todo se pasa a **kg**. g, libra y qq se convierten exacto. Para **litros** se usa el peso por litro del producto
  (por defecto 1 kg/l). Para **unidades** (huevos, piezas) se usa el peso por unidad del producto; si no lo tiene,
  esa línea **no suma** y se avisa («falta el peso de 1 huevo»).
- **Salió bueno (kg)** de una receta = unidades × peso por unidad del estándar. Si la receta no tiene peso por unidad,
  se usa el peso de sus ingredientes × (1 − pérdida normal).
- **Pérdida normal (kg)** = salió bueno ÷ (1 − p) − salió bueno, con p = % de pérdida normal de la receta (por
  defecto 3 %).
- **Tolerancia** del turno = promedio de la tolerancia de las recetas, pesado por lo producido (por defecto 2 %).
- **Sin explicar (kg)** = entró − salió bueno − pérdida normal − anotado. Positivo = **falta** (entró más de lo que se
  explica: lo normal cuando hay fuga). Negativo = **sobra** (se explica más de lo que entró: falta anotar una entrega,
  o la receta pide más de lo que se usa de verdad: revisar el estándar).
- **Sin explicar (%)** = sin explicar ÷ entró. **Alarma** si |%| > tolerancia.
- **Dinero** = kg sin explicar × costo promedio por kg de lo entregado (precio más barato vigente de cada producto).
- Lo producido sale del informe del turno si el chef lo corrigió; si no, de las ventas registradas.
- Las mermas ahora pueden llevar **turno**. Las que no lo tienen se muestran aparte («merma del día sin turno») y no
  entran al balance de ningún turno, para no contar dos veces.

## 5. Datos nuevos

| Tabla / columna | Para qué |
|---|---|
| `EstandaresReceta` (receta, peso por unidad g, pérdida normal %, tolerancia %) | lo «normal» de cada receta |
| `Catalogo.kg_por_unidad` | peso de 1 unidad o de 1 litro de un producto |
| `MovimientosTurno` (fecha, turno, entrega/devolución, producto, cantidad, unidad, quién entregó, quién recibió) | lo que entra al turno; **descuenta del inventario** (la devolución lo suma) |
| `SalidasTurno` (fecha, turno, tipo: comida del personal / residuo de limpieza / muestra / otro, kg, nota) | lo que se va sin ser merma ni venta |
| `Mermas.turno` | merma pesada de cada turno |
| `producido[].recibido` en el informe del turno | unidades contadas por otra persona |

Al **firmar** el informe del turno, el balance queda guardado como foto (no cambia después).

## 6. Pantallas

En **Informe del turno**, una sección nueva **Balance del turno**:
- Tarjetas: entró, salió bueno, pérdida normal, anotado, **sin explicar** (kg, % y dinero) con semáforo
  (verde dentro de la tolerancia, ámbar cerca, rojo en alarma).
- Barra apilada de la entrada repartida en sus partes.
- Tabla **por ingrediente** ordenada por la fuga en dinero.
- Tabla **por unidades**: producido, recibido, vendido, diferencia.
- Botones para anotar: **Entrega de bodega**, **Devolución a bodega**, **Merma pesada**, **Comida del personal**,
  **Residuo de limpieza**. Cada registro guarda quién lo hizo.
- Avisos claros: «faltan entregas de bodega para este turno», «falta el peso por unidad de: …».

En **Recetas**, en la ficha: **Estándar de producción** (peso por unidad, pérdida normal %, tolerancia %), con la
explicación de cómo medirlo: pesar lo que entra y lo que sale bueno en 3 a 5 tandas y tomar el promedio.

En **Panel del dueño → Análisis**: **Pérdida sin explicar por turno**: gráfica por día y turno de las últimas semanas
y lista de los turnos en alarma. Así se ve si siempre falla el mismo turno, el mismo producto o el mismo equipo.

## 7. Qué NO hace (honesto)

- No impide el robo ni el descuido. Hace que se vean **en el mismo turno, con producto y turno**, no años después.
- Si bodega no anota sus entregas, no hay balance: la pantalla lo dice.
- Los estándares de pérdida hay que medirlos en la cocina real. Los de la demostración son supuestos.
- Si los pesos los toma la misma persona que produce, el control se debilita: se recomienda que bodega entregue y
  otra persona cuente lo recibido.

## 8. Pruebas que deben pasar

- El ejemplo de la panadería da exactamente los números de la tabla.
- Conversión de g, libra, qq, litros (con peso por litro) y unidades (con peso por unidad; sin peso → aviso).
- Una entrega descuenta el inventario (lo que vence antes primero) y una devolución lo suma.
- Por ingrediente: entregado − devuelto − uso por receta − merma = diferencia, a mano.
- Alarma dentro y fuera de la tolerancia; signo de falta y sobra.
- Mermas con turno entran; sin turno quedan aparte.
- El informe firmado guarda el balance y ya no cambia.
- Datos malos: cantidades 0 o negativas, unidades raras, fecha futura, turno firmado (no se puede anotar).
- Pantalla: anotar entrega y merma, ver el balance cambiar, firmar e imprimir (prueba con clics).

## 9. Datos de demostración

Para los últimos 7 días: entregas de bodega por turno calculadas desde lo producido y sus recetas, más una fuga
normal de 0 a 2 %, y **un turno con fuga de 7 %** para que se vea la alarma. Mermas con turno, comida del personal
y residuos de limpieza. Todo marcado como demostración.
