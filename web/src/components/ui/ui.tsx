import { useEffect, useRef, type ButtonHTMLAttributes, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { AlertTriangle, Inbox, X } from "lucide-react";
import type { Semaforo } from "../../lib/format";

export const cx = (...c: (string | false | null | undefined)[]) => c.filter(Boolean).join(" ");

export const tono: Record<Semaforo, string> = {
  bad: "text-bad bg-bad/15 border-bad/40",
  warn: "text-warn bg-warn/15 border-warn/40",
  ok: "text-ok bg-ok/15 border-ok/40",
};
export const puntoTono: Record<Semaforo, string> = { bad: "bg-bad", warn: "bg-warn", ok: "bg-ok" };

export function Card({ className, children, ...p }: { className?: string; children: ReactNode } & React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cx("rounded-2xl border border-line bg-surface p-5", className)} {...p}>{children}</div>;
}

type BtnProps = ButtonHTMLAttributes<HTMLButtonElement> & { variante?: "primario" | "suave" | "peligro" };
export function Button({ variante = "suave", className, ...p }: BtnProps) {
  const v = {
    primario: "bg-brand text-black hover:brightness-110 font-semibold",
    suave: "border border-line hover:bg-line/50",
    peligro: "border border-bad/50 text-bad hover:bg-bad/10",
  }[variante];
  return (
    <button
      className={cx("inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm transition disabled:cursor-not-allowed disabled:opacity-50", v, className)}
      {...p}
    />
  );
}

export function Badge({ nivel, children }: { nivel: Semaforo; children: ReactNode }) {
  return (
    <span className={cx("inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium", tono[nivel])}>
      <span className={cx("h-1.5 w-1.5 rounded-full", puntoTono[nivel])} aria-hidden />
      {children}
    </span>
  );
}

export const Skeleton = ({ className }: { className?: string }) => <div className={cx("skeleton", className)} aria-hidden />;

export function Cargando({ filas = 4 }: { filas?: number }) {
  return (
    <div className="space-y-3" role="status" aria-label="Cargando">
      {Array.from({ length: filas }, (_, i) => <Skeleton key={i} className="h-10 w-full" />)}
    </div>
  );
}

export function ErrorCaja({ error, onReintentar }: { error: unknown; onReintentar?: () => void }) {
  const msg = error instanceof Error ? error.message : "Algo salió mal.";
  return (
    <Card role="alert" className="flex flex-wrap items-center gap-3 border-bad/40">
      <AlertTriangle className="text-bad" aria-hidden />
      <p className="flex-1">{msg}</p>
      {onReintentar && <Button onClick={onReintentar}>Reintentar</Button>}
    </Card>
  );
}

export function Vacio({ titulo, texto }: { titulo: string; texto?: string }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-2xl border border-dashed border-line p-10 text-center">
      <Inbox className="text-muted" aria-hidden />
      <p className="font-medium">{titulo}</p>
      {texto && <p className="max-w-md text-sm text-muted">{texto}</p>}
    </div>
  );
}

export function Pagina({ titulo, subtitulo, accion, children }: { titulo: string; subtitulo?: string; accion?: ReactNode; children: ReactNode }) {
  return (
    <div className="rise mx-auto w-full max-w-6xl p-4 sm:p-8">
      {/* no-print: cada pantalla imprimible pone su propio encabezado (así no sale el título dos veces) */}
      <div className="no-print flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold sm:text-3xl">{titulo}</h1>
          {subtitulo && <p className="mt-1 text-muted">{subtitulo}</p>}
        </div>
        {accion && <div className="no-print">{accion}</div>}
      </div>
      <div className="mt-6 space-y-6">{children}</div>
    </div>
  );
}

export function Pestanas<T extends string>({ valor, onCambia, items }: { valor: T; onCambia: (v: T) => void; items: { id: T; nombre: string }[] }) {
  return (
    <div role="tablist" className="no-print inline-flex flex-wrap gap-1 rounded-xl border border-line bg-surface p-1">
      {items.map((i) => (
        <button
          key={i.id} role="tab" aria-selected={valor === i.id} onClick={() => onCambia(i.id)}
          className={cx("rounded-lg px-4 py-1.5 text-sm font-medium transition", valor === i.id ? "bg-brand text-black" : "text-muted hover:text-ink")}
        >
          {i.nombre}
        </button>
      ))}
    </div>
  );
}

export function Dialogo({ titulo, onCerrar, children }: { titulo: string; onCerrar: () => void; children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  // onCerrar cambia en cada render del padre: se guarda aparte para que escribir en un campo NO le quite el foco
  const cerrar = useRef(onCerrar);
  cerrar.current = onCerrar;
  useEffect(() => {
    const caja = ref.current;
    (caja?.querySelector<HTMLElement>("input:not([type=hidden]):not([type=checkbox]),select,textarea") ?? caja?.querySelector<HTMLElement>("button"))?.focus();
    const f = (e: KeyboardEvent) => e.key === "Escape" && cerrar.current();
    window.addEventListener("keydown", f);
    return () => window.removeEventListener("keydown", f);
  }, []);
  // Se dibuja en <body>: así ningún contenedor animado (que crea su propia capa) lo deja debajo de la burbuja del asistente
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onMouseDown={(e) => e.target === e.currentTarget && onCerrar()}>
      <div ref={ref} role="dialog" aria-modal="true" aria-label={titulo} className="rise max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-line bg-surface p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">{titulo}</h2>
          <button aria-label="Cerrar" onClick={onCerrar} className="rounded-lg p-1 hover:bg-line/50"><X /></button>
        </div>
        {children}
      </div>
    </div>,
    document.body,
  );
}

export const Tabla = ({ children }: { children: ReactNode }) => (
  // relative: los textos solo-para-lector (sr-only, absolutos) quedan dentro y no estiran la página a lo ancho
  <div className="relative overflow-x-auto rounded-2xl border border-line bg-surface">
    <table className="w-full text-left text-sm">{children}</table>
  </div>
);
export const Th = ({ children, className }: { children?: ReactNode; className?: string }) => (
  <th scope="col" className={cx("border-b border-line px-4 py-3 font-semibold text-muted", className)}>{children}</th>
);
export const Td = ({ children, className }: { children?: ReactNode; className?: string }) => (
  <td className={cx("border-b border-line/60 px-4 py-3", className)}>{children}</td>
);

const TIPOS = [{ id: "", nombre: "Todo" }, { id: "alimento", nombre: "Alimentos" }, { id: "limpieza", nombre: "Limpieza" }];

/** Filtro "Todo | Alimentos | Limpieza". El valor vacío significa todo. */
export function FiltroTipo({ valor, onCambia }: { valor: string; onCambia: (v: string) => void }) {
  return (
    <div role="group" aria-label="Tipo de producto" className="inline-flex gap-1 rounded-xl border border-line bg-surface p-1">
      {TIPOS.map((t) => (
        <button key={t.id} type="button" aria-pressed={valor === t.id} onClick={() => onCambia(t.id)}
          className={cx("rounded-lg px-3 py-1 text-sm font-medium transition", valor === t.id ? "bg-brand text-black" : "text-muted hover:text-ink")}>
          {t.nombre}
        </button>
      ))}
    </div>
  );
}