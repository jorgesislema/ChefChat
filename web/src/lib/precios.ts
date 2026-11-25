import type { Semaforo } from "./format";

export type Unidad = "kg" | "l" | "unidad";

const NOMBRE_UNIDAD: Record<Unidad, string> = { kg: "kg", l: "litro", unidad: "unidad" };

const num = (n: number, dec = 2) => n.toFixed(dec).replace(".", ",");

/** "$12,15" */
export const precio = (n: number) => `$${num(n)}`;

/** 12.15, "kg" -> "$12,15 por kg" */
export const precioConUnidad = (n: number, u: Unidad) => `${precio(n)} por ${NOMBRE_UNIDAD[u]}`;

export interface CambioPrecio { flecha: "↑" | "↓" | "="; texto: string; nivel: Semaforo | null }

/** Cambio frente al precio anterior: subir = rojo, bajar = verde, sin cambio = sin color. */
export function cambioPrecio(pct: number | null): CambioPrecio | null {
  if (pct === null) return null;
  const r = Math.round(pct * 10) / 10;
  if (r === 0) return { flecha: "=", texto: "± 0 %", nivel: null };
  const t = `${Math.abs(r).toString().replace(".", ",")} %`;
  return r > 0 ? { flecha: "↑", texto: `+${t}`, nivel: "bad" } : { flecha: "↓", texto: `-${t}`, nivel: "ok" };
}

/** Margen: verde desde 60 %, ámbar de 30 a 60 %, rojo por debajo de 30 %. */
export const nivelMargen = (pct: number): Semaforo => (pct >= 60 ? "ok" : pct >= 30 ? "warn" : "bad");

export const textoMargen = (pct: number) => `${Math.round(pct)} %`;
