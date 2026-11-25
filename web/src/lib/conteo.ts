import type { CostoReal, LineaConteo } from "./api";
import type { Semaforo } from "./format";

/**
 * Lee lo que escribió la persona: "2,5" o "2.5" → 2.5; vacío → null (sin contar);
 * cualquier cosa que no sea un número de cero para arriba → NaN.
 */
export function leerCantidad(texto: string): number | null {
  const t = texto.trim().replace(",", ".");
  if (t === "") return null;
  if (!/^\d*\.?\d+$|^\d+\.$/.test(t)) return NaN;
  return Number(t);
}

/** Cantidad para mostrar en el campo: 2.5 → "2,5"; sin contar → "". */
export const textoCantidad = (n: number | null | undefined): string =>
  n === null || n === undefined ? "" : String(Math.round(n * 1000) / 1000).replace(".", ",");

/** Lo contado menos lo que dice el sistema (negativo = falta). Null si no hay conteo. */
export function diferencia(sistema: number, contada: number | null): number | null {
  if (contada === null || Number.isNaN(contada)) return null;
  return Math.round((contada - sistema) * 1000) / 1000;
}

export type NivelDif = { nivel: Semaforo; texto: "Falta" | "Sobra" | "Igual" };

/** Falta = rojo, sobra = ámbar, igual = verde. Null mientras no se cuente. */
export function nivelDiferencia(dif: number | null): NivelDif | null {
  if (dif === null) return null;
  if (dif === 0) return { nivel: "ok", texto: "Igual" };
  return dif < 0 ? { nivel: "bad", texto: "Falta" } : { nivel: "warn", texto: "Sobra" };
}

/** Texto con signo: "+1,5", "-2", "0". */
export function textoDiferencia(dif: number): string {
  const t = textoCantidad(Math.abs(dif));
  return dif > 0 ? `+${t}` : dif < 0 ? `-${t}` : "0";
}

/** Porcentaje de avance entero (0 a 100). */
export const avancePct = (contadas: number, total: number): number =>
  total <= 0 ? 0 : Math.min(100, Math.round((contadas / total) * 100));

export type ChipConteo = "todos" | "sin_contar" | "con_diferencia";

/** Filtra por nombre, categoría y chip. Usa lo guardado, para que una fila no desaparezca mientras se escribe en ella. */
export function filtrarLineas(lineas: LineaConteo[], f: { q?: string; categoria?: string; chip?: ChipConteo }): LineaConteo[] {
  const q = (f.q ?? "").trim().toLowerCase();
  return lineas.filter((l) => {
    if (q && !l.producto.toLowerCase().includes(q)) return false;
    if (f.categoria && l.categoria !== f.categoria) return false;
    if (f.chip === "sin_contar") return l.cantidad_contada === null;
    if (f.chip === "con_diferencia") return (diferencia(l.cantidad_sistema, l.cantidad_contada) ?? 0) !== 0;
    return true;
  });
}

export interface CambioConteo { producto_id: number; cantidad: number | null }

/**
 * Arma el cuerpo de «contar»: solo lo que cambió frente a lo guardado.
 * `escrito` tiene el texto de cada campo editado (por producto_id). Los textos inválidos no se envían y se cuentan aparte.
 */
export function cuerpoContar(lineas: LineaConteo[], escrito: Record<number, string>): { cambios: CambioConteo[]; invalidos: number } {
  const cambios: CambioConteo[] = [];
  let invalidos = 0;
  for (const l of lineas) {
    const t = escrito[l.producto_id];
    if (t === undefined) continue;
    const n = leerCantidad(t);
    if (n !== null && Number.isNaN(n)) { invalidos++; continue; }
    if (n === l.cantidad_contada) continue;
    cambios.push({ producto_id: l.producto_id, cantidad: n });
  }
  return { cambios, invalidos };
}

export const SIN_CATEGORIA = "Sin categoría";

/** Agrupa por categoría (orden alfabético, «Sin categoría» al final) y los productos por nombre. */
export function agruparPorCategoria(lineas: LineaConteo[]): { categoria: string; lineas: LineaConteo[] }[] {
  const mapa = new Map<string, LineaConteo[]>();
  for (const l of lineas) {
    const c = l.categoria?.trim() || SIN_CATEGORIA;
    mapa.set(c, [...(mapa.get(c) ?? []), l]);
  }
  return [...mapa.entries()]
    .sort(([a], [b]) => (a === SIN_CATEGORIA ? 1 : b === SIN_CATEGORIA ? -1 : a.localeCompare(b, "es")))
    .map(([categoria, ls]) => ({ categoria, lineas: [...ls].sort((x, y) => x.producto.localeCompare(y.producto, "es")) }));
}

/** Valores que se verán al cerrar. Si se usa «lo que dice el sistema» para lo no contado, ese valor se suma a lo contado. */
export function resumenCierre(lineas: LineaConteo[], sistemaActual: number, contadoActual: number, sinContarIgual: boolean) {
  const sinContar = lineas.filter((l) => l.cantidad_contada === null);
  const extra = sinContarIgual ? sinContar.reduce((s, l) => s + (l.valor_sistema ?? 0), 0) : 0;
  const contado = Math.round((contadoActual + extra) * 100) / 100;
  return { sinContar: sinContar.length, sistema: sistemaActual, contado, diferencia: Math.round((contado - sistemaActual) * 100) / 100 };
}

/** Datos de la fila «Inventario inicial + compras − inventario final = usaste». Null si falta algún conteo. */
export function filaUsado(d: Pick<CostoReal, "metodo" | "comprado" | "inventario_inicial" | "inventario_final" | "real">) {
  if (d.metodo !== "conteo" || !d.inventario_inicial || !d.inventario_final) return null;
  return {
    fechaInicial: d.inventario_inicial.fecha, inicial: d.inventario_inicial.valor, comprado: d.comprado,
    fechaFinal: d.inventario_final.fecha, final: d.inventario_final.valor, usado: d.real,
  };
}
