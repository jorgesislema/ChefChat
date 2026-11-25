import type { PeriodoDatos } from "./api";
import type { Semaforo } from "./format";

const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

/** Un mes con menos de estos días con datos se marca como parcial. */
export const DIAS_MES_COMPLETO = 20;

/** Fecha local "AAAA-MM-DD" (no usa UTC, para que "hoy" sea el día del usuario). */
export function fechaISO(d: Date): string {
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

export interface Atajo { id: "todo" | "30" | "90"; nombre: string; desde: string; hasta: string }

/** Atajos del filtro de fechas. "Todo" deja ambas fechas vacías; los demás terminan hoy e incluyen hoy. */
export function atajosFechas(hoy: Date): Atajo[] {
  const atras = (dias: number) => {
    const d = new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate() - (dias - 1));
    return fechaISO(d);
  };
  const h = fechaISO(hoy);
  return [
    { id: "todo", nombre: "Todo", desde: "", hasta: "" },
    { id: "30", nombre: "Últimos 30 días", desde: atras(30), hasta: h },
    { id: "90", nombre: "Últimos 90 días", desde: atras(90), hasta: h },
  ];
}

function partes(iso: string): { d: number; m: number; y: number } | null {
  const r = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!r) return null;
  const [y, m, d] = [Number(r[1]), Number(r[2]), Number(r[3])];
  return m >= 1 && m <= 12 ? { d, m, y } : null;
}

/** "Datos del 19 abr al 19 may 2026". Maneja fechas vacías, un solo día y años distintos. */
export function textoPeriodo(p: PeriodoDatos | null | undefined): string {
  const a = p?.desde ? partes(p.desde) : null;
  const b = p?.hasta ? partes(p.hasta) : null;
  if (!a || !b) return "No hay datos en estas fechas";
  const corta = (x: typeof a) => `${x.d} ${MESES[x.m - 1]}`;
  if (a.y === b.y && a.m === b.m && a.d === b.d) return `Datos del ${corta(a)} ${a.y}`;
  if (a.y === b.y) return `Datos del ${corta(a)} al ${corta(b)} ${b.y}`;
  return `Datos del ${corta(a)} ${a.y} al ${corta(b)} ${b.y}`;
}

/** Ancho de barra de 0 a 100. Devuelve 0 si el máximo no es positivo o el valor no es un número. */
export function anchoBarra(valor: number, maximo: number): number {
  if (!Number.isFinite(valor) || !Number.isFinite(maximo) || maximo <= 0 || valor <= 0) return 0;
  return Math.min(100, (valor / maximo) * 100);
}

/** Verde desde 60 %, ámbar de 30 a menos de 60 %, rojo por debajo. Sin dato: null. */
export function nivelMargen(pct: number | null | undefined): Semaforo | null {
  if (pct === null || pct === undefined || !Number.isFinite(pct)) return null;
  return pct >= 60 ? "ok" : pct >= 30 ? "warn" : "bad";
}

/** Nota para un mes con pocos días de datos; null si el mes está completo. */
export function etiquetaParcial(diasConDatos: number): string | null {
  if (diasConDatos >= DIAS_MES_COMPLETO) return null;
  return `datos parciales (${diasConDatos} ${diasConDatos === 1 ? "día" : "días"})`;
}

/** Porcentaje para mostrar: "12,5 %" o "-" si no hay dato. */
export function textoPct(p: number | null | undefined): string {
  return p === null || p === undefined || !Number.isFinite(p) ? "-" : `${String(Math.round(p * 10) / 10).replace(".", ",")} %`;
}

/** Texto de un monto escrito por el usuario ("12,50") a número en dólares. Vacío = undefined; inválido = null. */
export function leerDolares(t: string): number | undefined | null {
  const s = t.trim().replace(",", ".");
  if (s === "") return undefined;
  if (!/^\d+(\.\d{1,2})?$/.test(s)) return null;
  const n = Number(s);
  return n <= 100000 ? n : null;
}
