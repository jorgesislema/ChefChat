export type Semaforo = "bad" | "warn" | "ok";

const MS_DIA = 86_400_000;

/** Días entre hoy y una fecha "YYYY-MM-DD" (negativo si ya pasó). */
export function diasRestantes(vence: string, hoy: Date = new Date()): number {
  const [y, m, d] = vence.split("-").map(Number);
  const a = Date.UTC(y, m - 1, d);
  const b = Date.UTC(hoy.getFullYear(), hoy.getMonth(), hoy.getDate());
  return Math.round((a - b) / MS_DIA);
}

export function etiquetaDias(dias: number): string {
  if (dias < -1) return `Venció hace ${-dias} días`;
  if (dias === -1) return "Venció ayer";
  if (dias === 0) return "Vence hoy";
  if (dias === 1) return "Vence mañana";
  return `Vence en ${dias} días`;
}

export function semaforo(dias: number): Semaforo {
  return dias <= 3 ? "bad" : dias <= 10 ? "warn" : "ok";
}

const _dinero = new Intl.NumberFormat("es-EC", { style: "currency", currency: "USD", maximumFractionDigits: 2 });
/** $1.234,56 — y los negativos como -$184,38 (no $-184,38). */
export const dinero = (n: number | null | undefined) => {
  const v = n ?? 0;
  return v < 0 ? `-${_dinero.format(-v)}` : _dinero.format(v);
};

export const fechaLarga = (iso: string) => {
  const [y, m, d] = iso.split("-").map(Number);
  const t = new Intl.DateTimeFormat("es", { weekday: "long", day: "numeric", month: "long", year: "numeric" })
    .format(new Date(y, m - 1, d));
  return t.charAt(0).toUpperCase() + t.slice(1);
};

/** Para usar en medio de una frase: «Conteo del miércoles, 25 de noviembre de 2026». */
export const fechaEnFrase = (iso: string) => fechaLarga(iso).toLowerCase();
