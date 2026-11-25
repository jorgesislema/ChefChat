import type { EstadoBalance, KgBalance } from "./api";

/** "12,3 kg": coma decimal y un decimal. Evita "-0,0". */
export function kg(n: number | null | undefined): string {
  const v = Math.round((n ?? 0) * 10) / 10;
  return `${(v === 0 ? 0 : v).toFixed(1).replace(".", ",")} kg`;
}

/** Porcentaje con coma y un decimal; "—" si no hay dato. */
export const pct = (n: number | null | undefined): string =>
  n === null || n === undefined ? "—" : `${(Math.round(n * 10) / 10).toFixed(1).replace(".", ",")} %`;

export const etiquetaEstado = (e: EstadoBalance): string =>
  ({ bien: "Bien", cerca: "Cerca del límite", alarma: "Alarma", sin_entregas: "Sin entregas de bodega", sin_datos: "Sin datos" })[e] ?? "Sin datos";

/** Colores del semáforo (clases Tailwind del proyecto). Gris para los estados sin cálculo. */
export function colorEstado(e: EstadoBalance): { caja: string; punto: string; texto: string } {
  switch (e) {
    case "bien": return { caja: "border-ok/40 bg-ok/15", punto: "bg-ok", texto: "text-ok" };
    case "cerca": return { caja: "border-warn/40 bg-warn/15", punto: "bg-warn", texto: "text-warn" };
    case "alarma": return { caja: "border-bad/40 bg-bad/15", punto: "bg-bad", texto: "text-bad" };
    default: return { caja: "border-line bg-line/30", punto: "bg-muted", texto: "text-muted" };
  }
}

export interface Tramo { clave: "bueno" | "normal" | "anotado" | "sin_explicar"; etiqueta: string; kg: number; pct: number; color: string }

/**
 * Tramos de la barra apilada, en % de lo que entró. Si sin_explicar es negativo (sobra) no hay tramo: se avisa aparte.
 * Los tramos no pasan de 100 % en total.
 */
export function tramosBarra(k: KgBalance): Tramo[] {
  if (!(k.entro > 0)) return [];
  const base: Omit<Tramo, "pct">[] = [
    { clave: "bueno", etiqueta: "Salió bueno", kg: Math.max(0, k.salio_bueno), color: "bg-ok" },
    { clave: "normal", etiqueta: "Pérdida normal", kg: Math.max(0, k.perdida_normal), color: "bg-brand" },
    { clave: "anotado", etiqueta: "Anotado", kg: Math.max(0, k.anotado), color: "bg-warn" },
    { clave: "sin_explicar", etiqueta: "Sin explicar", kg: Math.max(0, k.sin_explicar), color: "bg-bad" },
  ];
  const total = base.reduce((s, t) => s + t.kg, 0);
  const div = Math.max(k.entro, total);
  return base.map((t) => ({ ...t, pct: (t.kg / div) * 100 }));
}
