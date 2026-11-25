import type { ParamsSugerencia } from "./api";

export const UMBRAL_DIFERENCIA_PCT = 30;

/** Aviso amable cuando el costo con precios de proveedores se aleja del anotado en el archivo. */
export function avisoDiferencia(pct: number | null | undefined): string | null {
  if (pct === null || pct === undefined || Math.abs(pct) <= UMBRAL_DIFERENCIA_PCT) return null;
  const n = Math.round(Math.abs(pct));
  return `Con tus precios actuales el plato saldría un ${n} % ${pct > 0 ? "más caro" : "más barato"} que lo anotado en el archivo.`;
}

/** Query string de /api/menu/sugerencia. Omite el tope si no es un número positivo y `sin` si está vacío. */
export function queryDeSugerencia(p: ParamsSugerencia): string {
  const q = new URLSearchParams();
  q.set("comidas", p.comidas.join(","));
  if (p.tope !== null && p.tope !== undefined && Number.isFinite(p.tope) && p.tope > 0) q.set("tope", String(p.tope));
  if (p.sin.length) q.set("sin", p.sin.join(","));
  q.set("dias", String(p.dias));
  q.set("por_vencer", p.por_vencer ? "true" : "false");
  q.set("semilla", String(p.semilla));
  return q.toString().replace(/%2C/g, ",");
}

/** Interpreta el valor del campo "costo máximo": acepta coma o punto; vacío o inválido = sin tope. */
export function leerTope(texto: string): number | null {
  const n = Number(texto.trim().replace(",", "."));
  return texto.trim() !== "" && Number.isFinite(n) && n > 0 ? n : null;
}

export const PESTANAS_MENU = ["cocinar", "armar", "costos", "sobrantes"] as const;
export type PestanaMenu = (typeof PESTANAS_MENU)[number];
export const pestanaMenu = (v: string | null): PestanaMenu =>
  (PESTANAS_MENU as readonly string[]).includes(v ?? "") ? (v as PestanaMenu) : "cocinar";

export const PLAZOS = [
  { id: 0, nombre: "Hoy" }, { id: 1, nombre: "Mañana" }, { id: 3, nombre: "3 días" }, { id: 7, nombre: "Esta semana" },
] as const;

export const NOMBRE_COMIDA: Record<string, string> = {
  desayuno: "Desayuno", almuerzo: "Almuerzo", merienda: "Merienda", cena: "Cena",
};

const UNIDADES: Record<string, string> = { kg: "kg", l: "litros", unidad: "unidades" };

/** { kg: 2.5 } -> "2,5 kg" */
export function textoStock(s: Partial<Record<string, number>>): string {
  return Object.entries(s)
    .filter(([, v]) => typeof v === "number")
    .map(([u, v]) => `${String(Math.round((v as number) * 100) / 100).replace(".", ",")} ${UNIDADES[u] ?? u}`)
    .join(" y ");
}
