import type { CostoReal, UnidadPrecio } from "./api";
import { fechaISO } from "./analisis";

/** Unidades en las que se puede anotar la cantidad comprada. */
export const UNIDADES_CANTIDAD = [
  { id: "kg", nombre: "kg" }, { id: "g", nombre: "gramos" }, { id: "l", nombre: "litros" }, { id: "ml", nombre: "ml" },
  { id: "libra", nombre: "libras" }, { id: "qq", nombre: "quintales" }, { id: "unidad", nombre: "unidades" },
] as const;

export const UNIDADES_PRECIO: { id: UnidadPrecio; nombre: string }[] = [
  { id: "kg", nombre: "kg" }, { id: "l", nombre: "litro" }, { id: "unidad", nombre: "unidad" },
];

/** Cuánto vale 1 de cada unidad en la unidad base del precio. */
const FACTOR: Record<UnidadPrecio, Record<string, number>> = {
  kg: { kg: 1, g: 0.001, libra: 0.45359237, qq: 45.359237 },
  l: { l: 1, ml: 0.001 },
  unidad: { unidad: 1 },
};

/** Pasa una cantidad a la unidad del precio. null si esa unidad no se puede pasar (por ejemplo ml a kg). */
export function convertirCantidad(cantidad: number, unidad: string, a: UnidadPrecio): number | null {
  const f = FACTOR[a][unidad];
  return f === undefined || !Number.isFinite(cantidad) ? null : cantidad * f;
}

/** Total de una compra con la misma regla del servidor: cantidad en la unidad del precio × precio, a 2 decimales. */
export function totalCompra(cantidad: number, unidad: string, precio: number, unidadPrecio: UnidadPrecio): number | null {
  const c = convertirCantidad(cantidad, unidad, unidadPrecio);
  if (c === null || !Number.isFinite(precio)) return null;
  return Math.round(c * precio * 100) / 100;
}

export interface AtajoCompras { id: string; nombre: string; desde: string; hasta: string }

/** Atajos de fechas de Compras. "Todo" deja las dos fechas vacías. */
export function atajosCompras(hoy: Date): AtajoCompras[] {
  const h = fechaISO(hoy);
  const atras = (dias: number) => fechaISO(new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate() - (dias - 1)));
  return [
    { id: "mes", nombre: "Este mes", desde: fechaISO(new Date(hoy.getFullYear(), hoy.getMonth(), 1)), hasta: h },
    { id: "30", nombre: "Últimos 30 días", desde: atras(30), hasta: h },
    { id: "90", nombre: "Últimos 90 días", desde: atras(90), hasta: h },
    { id: "todo", nombre: "Todo", desde: "", hasta: "" },
  ];
}

export interface ParteBarra { clave: "vendido" | "sobreproduccion" | "merma_registrada" | "sin_explicar"; etiqueta: string; monto: number; pct: number }

const ETIQUETAS: Record<ParteBarra["clave"], string> = {
  vendido: "Lo que se vendió", sobreproduccion: "Lo que sobró de más", merma_registrada: "Merma anotada", sin_explicar: "Sin explicar",
};

/**
 * Partes de la barra apilada. Solo entran los montos positivos; los porcentajes suman 100.
 * Si "sin explicar" es negativo (gastaste menos de lo esperado) no se dibuja y `gastoMenor` es true.
 */
export function partesBarra(d: NonNullable<CostoReal["desglose"]>): { partes: ParteBarra[]; gastoMenor: boolean } {
  const claves = ["vendido", "sobreproduccion", "merma_registrada", "sin_explicar"] as const;
  const validas = claves.filter((k) => Number.isFinite(d[k]) && d[k] > 0);
  const total = validas.reduce((s, k) => s + d[k], 0);
  const partes = validas.map((k) => ({ clave: k, etiqueta: ETIQUETAS[k], monto: d[k], pct: (d[k] / total) * 100 }));
  return { partes, gastoMenor: d.sin_explicar < 0 };
}

export { ETIQUETAS as ETIQUETAS_BARRA };
