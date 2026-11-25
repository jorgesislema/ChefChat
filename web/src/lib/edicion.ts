import type { EditaLote, EditaProducto, NuevoLote, TipoProducto } from "./api";

/** Unidades que acepta el servidor para un lote. */
export const UNIDADES_LOTE = ["kg", "g", "l", "ml", "libra", "qq", "unidad"] as const;

/** Convierte "12,5" o "12.5" en número. Devuelve NaN si no es un número. */
export function aNumero(texto: string): number {
  const t = texto.trim().replace(",", ".");
  return t === "" ? NaN : Number(t);
}

/** "YYYY-MM-DD" de la fecha local (no UTC). */
export function hoyISO(hoy: Date = new Date()): string {
  const p = (n: number) => String(n).padStart(2, "0");
  return `${hoy.getFullYear()}-${p(hoy.getMonth() + 1)}-${p(hoy.getDate())}`;
}

/** Verdadero si es una fecha "YYYY-MM-DD" que existe en el calendario. */
export function fechaValida(f: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(f)) return false;
  const [y, m, d] = f.split("-").map(Number);
  const x = new Date(Date.UTC(y, m - 1, d));
  return x.getUTCFullYear() === y && x.getUTCMonth() === m - 1 && x.getUTCDate() === d;
}

/** Porcentaje de cambio entre dos precios, o null si no se puede calcular. */
export function porcentajeCambio(anterior: number | null | undefined, nuevo: number): number | null {
  if (anterior === null || anterior === undefined || !(anterior > 0) || !Number.isFinite(nuevo)) return null;
  return ((nuevo - anterior) / anterior) * 100;
}

/** Texto para mostrar antes de guardar un precio: «subirá 12 %», «bajará 8 %», «sin cambio». */
export function textoDiferenciaPrecio(anterior: number | null | undefined, nuevo: number): string {
  const pct = porcentajeCambio(anterior, nuevo);
  if (pct === null) return "";
  const r = Math.round(Math.abs(pct) * 10) / 10;
  if (r === 0) return "sin cambio";
  const t = r.toString().replace(".", ",");
  return pct > 0 ? `subirá ${t} %` : `bajará ${t} %`;
}

export interface FormLote {
  producto: string;
  cantidad: string;
  unidad: string;
  fechaIngreso: string;
  vence: string;
  idLote: string;
  categoria: string;
  /** Solo al editar: usar la vida útil del producto en lugar de una fecha fija. */
  usarVidaUtil?: boolean;
}

/** Mensajes en español de lo que falta o está mal. Lista vacía = se puede enviar. */
export function validarLote(f: FormLote, { editando = false }: { editando?: boolean } = {}): string[] {
  const m: string[] = [];
  if (!editando && f.producto.trim() === "") m.push("Escribe el nombre del producto.");
  const c = aNumero(f.cantidad);
  if (!Number.isFinite(c) || c <= 0) m.push("La cantidad debe ser un número mayor que cero.");
  if (!(UNIDADES_LOTE as readonly string[]).includes(f.unidad)) m.push("Elige una unidad.");
  const ingresoOk = fechaValida(f.fechaIngreso);
  if (!ingresoOk) m.push("La fecha de ingreso no es válida.");
  const venceUsado = f.vence.trim() !== "" && !f.usarVidaUtil;
  const venceOk = venceUsado && fechaValida(f.vence);
  if (venceUsado && !venceOk) m.push("La fecha de vencimiento no es válida.");
  if (ingresoOk && venceOk && f.vence < f.fechaIngreso) m.push("El vencimiento no puede ser antes del ingreso.");
  return m;
}

/** Cuerpo para crear un lote. La categoría solo viaja si el producto es nuevo. */
export function cuerpoNuevoLote(f: FormLote, productoExiste: boolean): NuevoLote {
  const b: NuevoLote = {
    producto: f.producto.trim(), cantidad: aNumero(f.cantidad), unidad: f.unidad, fecha_ingreso: f.fechaIngreso,
  };
  if (f.vence.trim()) b.fecha_caducidad = f.vence.trim();
  if (f.idLote.trim()) b.id_lote = f.idLote.trim();
  if (!productoExiste && f.categoria.trim()) b.categoria = f.categoria.trim();
  return b;
}

/** Cuerpo para editar un lote. Con «usar vida útil» manda quitar_caducidad y no manda fecha. */
export function cuerpoEditaLote(f: FormLote): EditaLote {
  const b: EditaLote = { cantidad: aNumero(f.cantidad), unidad: f.unidad, fecha_ingreso: f.fechaIngreso };
  if (f.usarVidaUtil) b.quitar_caducidad = true;
  else if (f.vence.trim()) b.fecha_caducidad = f.vence.trim();
  return b;
}

export interface FormProducto { nombre: string; categoria: string; tipo: TipoProducto; vidaUtil: string }

export function validarProducto(f: FormProducto): string[] {
  const m: string[] = [];
  if (f.nombre.trim() === "") m.push("Escribe el nombre del producto.");
  if (f.vidaUtil.trim() !== "") {
    const v = aNumero(f.vidaUtil);
    if (!Number.isInteger(v) || v <= 0) m.push("La vida útil debe ser un número entero de días, mayor que cero.");
  }
  return m;
}

export function cuerpoEditaProducto(f: FormProducto): EditaProducto {
  const b: EditaProducto = { nombre: f.nombre.trim(), tipo: f.tipo };
  if (f.categoria.trim()) b.categoria = f.categoria.trim();
  if (f.vidaUtil.trim()) b.vida_util_dias = aNumero(f.vidaUtil);
  return b;
}
