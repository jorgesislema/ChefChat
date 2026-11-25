import type { DatosTurno, GuardaInforme, IncidenciaTurno, InformeTurno, TotalesTurno, Turno } from "./api";

export const TURNOS: { id: Turno; nombre: string }[] = [
  { id: "matutino", nombre: "Mañana" },
  { id: "vespertino", nombre: "Tarde" },
  { id: "nocturno", nombre: "Noche" },
];

export const MAX_OBSERVACIONES = 1000;

export const esTurno = (t: string | null): t is Turno => t === "matutino" || t === "vespertino" || t === "nocturno";

/** Nombre del turno para mostrar: Mañana, Tarde o Noche. */
export const nombreTurno = (t: Turno): string => TURNOS.find((x) => x.id === t)?.nombre ?? t;

/** Turno que toca según la hora (antes de las 12 Mañana, antes de las 18 Tarde, después Noche). */
export const turnoDeAhora = (ahora: Date = new Date()): Turno => {
  const h = ahora.getHours();
  return h < 12 ? "matutino" : h < 18 ? "vespertino" : "nocturno";
};

/** Fila editable de producido: los números se guardan como texto mientras se escribe. */
export interface FilaForm {
  clave: number;
  receta_id: string | null;
  plato: string;
  servicio: string | null;
  producido: string;
  vendido: string;
  costo_plato: number | null;
  /** unidades que contó otra persona (mostrador, despacho). Vacío = no se contó. */
  recibido: string;
}

export interface FormInforme {
  chefId: string;
  personal: string[];
  filas: FilaForm[];
  incidencias: IncidenciaTurno[];
  observaciones: string;
}

let contador = 0;
export const nuevaClave = () => ++contador;

/** Formulario inicial a partir de lo que trae el servidor. */
export function formDesdeInforme(inf: InformeTurno): FormInforme {
  return {
    chefId: inf.chef_id ?? "",
    personal: [...inf.personal],
    filas: inf.producido.map((p) => ({
      clave: nuevaClave(), receta_id: p.receta_id, plato: p.plato, servicio: p.servicio,
      producido: String(p.producido), vendido: String(p.vendido), costo_plato: p.costo_plato,
      recibido: p.recibido === null || p.recibido === undefined ? "" : String(p.recibido),
    })),
    incidencias: inf.incidencias.map((i) => ({ ...i })),
    observaciones: inf.observaciones ?? "",
  };
}

/** Entero ≥ 0 escrito como texto ("12"). Devuelve NaN si no lo es (vacío, negativo, decimal, letras). */
export function entero(texto: string): number {
  const t = texto.trim();
  return /^\d{1,9}$/.test(t) ? Number(t) : NaN;
}

const redondear = (n: number) => Math.round(n * 100) / 100;
const cero = (n: number) => (Number.isFinite(n) ? n : 0);

/** Sobrante de una fila: lo producido que no se vendió (nunca negativo). */
export const sobranteFila = (f: Pick<FilaForm, "producido" | "vendido">): number =>
  Math.max(cero(entero(f.producido)) - cero(entero(f.vendido)), 0);

/** Costo del sobrante de una fila, o null si el plato no tiene costo. */
export const costoSobranteFila = (f: FilaForm): number | null =>
  f.costo_plato === null ? null : redondear(sobranteFila(f) * f.costo_plato);

/** Totales del turno en vivo, con la misma regla del servidor. Merma, recuperado y compras vienen de `datos`. */
export function calcularTotales(filas: FilaForm[], datos: Pick<DatosTurno, "merma_total" | "recuperado_total" | "compras_total">): TotalesTurno {
  let producidos = 0, vendidos = 0, sobrantes = 0, costo = 0;
  for (const f of filas) {
    producidos += cero(entero(f.producido));
    vendidos += cero(entero(f.vendido));
    sobrantes += sobranteFila(f);
    costo += costoSobranteFila(f) ?? 0;
  }
  return {
    platos_producidos: producidos, platos_vendidos: vendidos, platos_sobrantes: sobrantes, costo_sobrante: redondear(costo),
    merma: datos.merma_total, recuperado: datos.recuperado_total, compras: datos.compras_total,
  };
}

/** Mensajes de error en español. Lista vacía = se puede enviar. `paraFirmar` exige chef y personal. */
export function validarInforme(f: FormInforme, paraFirmar: boolean): string[] {
  const m: string[] = [];
  f.filas.forEach((fila, i) => {
    const n = fila.plato.trim() || `La fila ${i + 1}`;
    if (!fila.plato.trim()) m.push(`La fila ${i + 1} no tiene nombre de plato.`);
    const p = entero(fila.producido), v = entero(fila.vendido);
    if (Number.isNaN(p)) m.push(`${n}: lo producido debe ser un número entero, 0 o más.`);
    if (Number.isNaN(v)) m.push(`${n}: lo vendido debe ser un número entero, 0 o más.`);
    if (!Number.isNaN(p) && !Number.isNaN(v) && v > p) m.push(`${n}: no puedes vender más de lo que produjiste.`);
    if ((fila.recibido ?? "").trim()) {
      const r = entero(fila.recibido);
      if (Number.isNaN(r)) m.push(`${n}: lo recibido debe ser un número entero, 0 o más (o déjalo vacío).`);
      else if (!Number.isNaN(p) && r > p) m.push(`${n}: no se puede recibir más de lo que se produjo.`);
    }
  });
  f.incidencias.forEach((inc, i) => {
    if (!inc.descripcion.trim()) m.push(`La incidencia ${i + 1} no tiene descripción.`);
  });
  if (f.observaciones.length > MAX_OBSERVACIONES) m.push(`Las observaciones pasan de ${MAX_OBSERVACIONES} letras.`);
  if (paraFirmar) {
    if (!f.chefId) m.push("Elige el chef del turno.");
    if (f.personal.length === 0) m.push("Marca al menos una persona que trabajó en el turno.");
  }
  return m;
}

/**
 * Cuerpo para guardar. No lleva `costo_plato`. Si el producido no se tocó y venía propuesto
 * por las ventas (`producidoEditado` false), manda null para que el servidor siga recalculándolo.
 */
export function cuerpoGuardar(fecha: string, turno: Turno, f: FormInforme, producidoSinTocar = false): GuardaInforme {
  return {
    fecha, turno,
    chef_id: f.chefId || null,
    personal: [...f.personal],
    producido: producidoSinTocar ? null : f.filas.map((x) => ({
      receta_id: x.receta_id, plato: x.plato.trim(), servicio: x.servicio, producido: entero(x.producido), vendido: entero(x.vendido),
      recibido: (x.recibido ?? "").trim() ? entero(x.recibido) : null,
    })),
    incidencias: f.incidencias.map((i) => ({ tipo: i.tipo, descripcion: i.descripcion.trim() })),
    observaciones: f.observaciones,
  };
}

const huella = (f: FormInforme) => JSON.stringify({
  c: f.chefId,
  p: [...f.personal].sort(),
  f: f.filas.map((x) => [x.receta_id, x.plato.trim(), x.servicio, x.producido.trim(), x.vendido.trim(), (x.recibido ?? "").trim()]),
  i: f.incidencias.map((x) => [x.tipo, x.descripcion.trim()]),
  o: f.observaciones,
});

/** Verdadero si el formulario difiere de lo cargado (para avisar de cambios sin guardar). */
export const hayCambios = (actual: FormInforme, cargado: FormInforme): boolean => huella(actual) !== huella(cargado);

/** Fecha y hora legibles de un texto ISO; si no se entiende, lo devuelve tal cual. */
export function fechaHora(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat("es", { day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit" }).format(d);
}

/** "AAAA-MM-DD" de hace `dias` días. */
export function hace(dias: number, hoy: Date = new Date()): string {
  const d = new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate() - dias);
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}
