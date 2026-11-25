import type { ReactNode } from "react";
import { Info } from "lucide-react";
import { Badge, Card, cx } from "../ui/ui";
import { anchoBarra, etiquetaParcial, textoPeriodo } from "../../lib/analisis";
import type { PeriodoDatos } from "../../lib/api";
import { dinero } from "../../lib/format";

/** Tarjeta de una sección del análisis: título, de qué fechas son los datos y "Lo importante". */
export function Seccion({ titulo, periodo, demo, mensajes, children }: {
  titulo: string; periodo?: PeriodoDatos | null; demo?: boolean; mensajes: string[]; children: ReactNode;
}) {
  return (
    <Card className="space-y-4" aria-label={titulo} role="region">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">{titulo}</h2>
        <div className="flex flex-wrap items-center gap-2">
          {periodo !== undefined && <span className="text-sm text-muted">{textoPeriodo(periodo)}</span>}
          {demo && <Badge nivel="warn">Datos de demostración</Badge>}
        </div>
      </div>
      {mensajes.length > 0 && (
        <div className="rounded-xl border border-brand/40 bg-brand/10 p-3">
          <p className="mb-1 flex items-center gap-1.5 text-sm font-semibold"><Info size={16} aria-hidden /> Lo importante</p>
          <ul className="list-disc space-y-1 pl-5 text-sm">{mensajes.map((m, i) => <li key={i}>{m}</li>)}</ul>
        </div>
      )}
      {children}
    </Card>
  );
}

export function Dato({ etiqueta, valor, nota, tono }: { etiqueta: string; valor: ReactNode; nota?: ReactNode; tono?: string }) {
  return (
    <div className="rounded-xl border border-line p-3">
      <p className="text-sm text-muted">{etiqueta}</p>
      <p className={cx("text-2xl font-bold tabular-nums", tono)}>{valor}</p>
      {nota && <p className="text-xs text-muted">{nota}</p>}
    </div>
  );
}

export interface Fila { clave: string; etiqueta: string; valor: number; detalle: string }

/** Barras horizontales hechas con divs. Cada fila dice su dato con texto; la barra es solo decoración. */
export function BarrasHorizontales({ titulo, filas, relleno = "bg-brand" }: { titulo: string; filas: Fila[]; relleno?: string }) {
  const max = Math.max(0, ...filas.map((f) => f.valor));
  return (
    <div>
      <h3 className="mb-2 font-medium">{titulo}</h3>
      {filas.length === 0 ? <p className="text-sm text-muted">Sin datos.</p> : (
        <ul className="space-y-2" aria-label={titulo}>
          {filas.map((f) => (
            <li key={f.clave}>
              <div className="flex items-baseline justify-between gap-3 text-sm">
                <span className="min-w-0 break-words font-medium">{f.etiqueta}</span>
                <span className="shrink-0 tabular-nums text-muted">{f.detalle}</span>
              </div>
              <div className="mt-1 h-2.5 rounded-full bg-line" aria-hidden>
                <div className={cx("h-2.5 rounded-full", relleno)} style={{ width: `${anchoBarra(f.valor, max)}%`, minWidth: f.valor > 0 ? "4px" : undefined }} />
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

const RAYAS = { backgroundImage: "repeating-linear-gradient(45deg, transparent 0 4px, rgba(255,255,255,.35) 4px 8px)" };

export interface Columna { clave: string; etiqueta: string; valor: number; dias: number }

/** Columnas por mes. Un mes con pocos días de datos se dibuja rayado y más claro, con su nota. */
export function ColumnasMes({ columnas }: { columnas: Columna[] }) {
  const max = Math.max(0, ...columnas.map((c) => c.valor));
  const resumen = "Dinero perdido por mes: " + columnas.map((c) => `${c.etiqueta} ${dinero(c.valor)}${etiquetaParcial(c.dias) ? ` (${etiquetaParcial(c.dias)})` : ""}`).join("; ");
  const hayParcial = columnas.some((c) => etiquetaParcial(c.dias));
  return (
    <div>
      <h3 className="mb-2 font-medium">Por mes</h3>
      <div role="img" aria-label={resumen} className="flex items-end justify-center gap-3">
        {columnas.map((c) => {
          const parcial = etiquetaParcial(c.dias);
          return (
            <div key={c.clave} className="flex w-full max-w-28 flex-1 flex-col items-center">
              <span className="mb-1 text-sm font-medium tabular-nums">{dinero(c.valor)}</span>
              <div className="flex h-36 w-full items-end rounded-lg bg-line/40">
                <div className={cx("w-full rounded-lg", parcial ? "border-2 border-dashed border-bad bg-bad/40" : "bg-bad")}
                  style={{ height: `${anchoBarra(c.valor, max)}%`, minHeight: c.valor > 0 ? "4px" : undefined, ...(parcial ? RAYAS : {}) }} />
              </div>
              <span className="mt-1 text-sm">{c.etiqueta}</span>
              {parcial && <span className="text-center text-xs text-muted">{parcial}</span>}
            </div>
          );
        })}
      </div>
      {hayParcial && <p className="mt-2 text-xs text-muted">Las barras rayadas son meses con pocos días anotados: el total de ese mes puede ser más alto.</p>}
    </div>
  );
}
