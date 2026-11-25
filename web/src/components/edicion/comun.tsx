import { useCallback, useEffect, useRef, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Confirmar } from "../Confirmar";
import { Dialogo } from "../ui/ui";

/** Clases de los campos de formulario (igual que en Proveedores). */
export const campo = "w-full rounded-xl border border-line bg-bg px-3 py-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand";

/** Prefijos de queryKey que dependen de inventario, precios, productos y proveedores. */
const CLAVES = [
  "proveedores", "proveedor", "alertas-precios", "catalogo", "inventario", "venc", "resumen",
  "recetas", "receta", "menu", "menu-costos", "menu-sugerencia", "menu-cocinar", "menu-sobrantes",
  "lotes-inv", "productos-inv", "precios-producto",
];

/** Devuelve una función que vuelve a pedir todo lo que un cambio puede afectar. */
export function useRefrescar() {
  const qc = useQueryClient();
  return useCallback(() => Promise.all(CLAVES.map((k) => qc.invalidateQueries({ queryKey: [k] }))), [qc]);
}

/** Función con identidad fija que siempre llama a la versión más reciente (evita que el diálogo robe el foco al re-renderizar). */
export function useEstable<A extends unknown[], R>(fn: (...a: A) => R) {
  const ref = useRef(fn);
  ref.current = fn;
  return useCallback((...a: A) => ref.current(...a), []);
}

/** Diálogo cuyo primer campo recibe el foco (el diálogo base enfoca el botón de cerrar). */
export function DialogoEdicion({ titulo, onCerrar, children }: { titulo: string; onCerrar: () => void; children: ReactNode }) {
  const cerrar = useEstable(onCerrar);
  const caja = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const t = setTimeout(() => caja.current?.querySelector<HTMLElement>("input:not([type=checkbox]),select,textarea")?.focus(), 0);
    return () => clearTimeout(t);
  }, []);
  return <Dialogo titulo={titulo} onCerrar={cerrar}><div ref={caja}>{children}</div></Dialogo>;
}

/** Confirmación para quitar algo, con función de cierre estable. */
export function ConfirmarQuitar(p: { titulo: string; texto: string; confirmar: string; deshacer?: string; alConfirmar: () => Promise<unknown>; alCerrar: () => void }) {
  const cerrar = useEstable(p.alCerrar);
  return <Confirmar {...p} alCerrar={cerrar} />;
}

export function Campo({ id, etiqueta, ayuda, className, children }: { id: string; etiqueta: string; ayuda?: string; className?: string; children: ReactNode }) {
  return (
    <div className={className}>
      <label htmlFor={id} className="mb-1 block text-sm font-medium">{etiqueta}</label>
      {children}
      {ayuda && <p id={`${id}-ayuda`} className="mt-1 text-xs text-muted">{ayuda}</p>}
    </div>
  );
}

/** Lista de mensajes de validación en español. */
export function Avisos({ mensajes }: { mensajes: string[] }) {
  if (mensajes.length === 0) return null;
  return (
    <ul role="alert" className="list-disc space-y-1 rounded-xl border border-bad/50 bg-bad/10 p-3 pl-7 text-sm text-bad">
      {mensajes.map((m) => <li key={m}>{m}</li>)}
    </ul>
  );
}
