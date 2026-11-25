import { useEffect } from "react";
import { Check, X } from "lucide-react";
import type { PreguntaPublica } from "../lib/api";
import { cx } from "./ui/ui";

export interface Props {
  pregunta: PreguntaPublica;
  /** índice de la opción elegida (campo `i`), si ya respondió */
  elegida?: number | null;
  /** índice de la opción correcta, solo en práctica tras responder */
  correcta?: number | null;
  deshabilitada?: boolean;
  onElegir: (i: number) => void;
}

/** Pregunta con opciones como tarjetas. Teclas 1-4 eligen la opción. */
export function PreguntaExamen({ pregunta, elegida = null, correcta = null, deshabilitada, onElegir }: Props) {
  useEffect(() => {
    if (deshabilitada) return;
    const f = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement;
      if (e.ctrlKey || e.metaKey || e.altKey || ["INPUT", "TEXTAREA", "SELECT"].includes(t.tagName)) return;
      const op = pregunta.opciones[Number(e.key) - 1];
      if (op) { e.preventDefault(); onElegir(op.i); }
    };
    window.addEventListener("keydown", f);
    return () => window.removeEventListener("keydown", f);
  }, [pregunta, deshabilitada, onElegir]);

  return (
    <div>
      <h2 className="text-xl font-semibold sm:text-2xl" id="enunciado">{pregunta.enunciado}</h2>
      <div className="mt-5 grid gap-3" role="group" aria-labelledby="enunciado">
        {pregunta.opciones.map((o, n) => {
          const esElegida = elegida === o.i;
          const esCorrecta = correcta === o.i;
          return (
            <button key={o.i} disabled={deshabilitada} onClick={() => onElegir(o.i)} aria-pressed={esElegida}
              className={cx("flex items-center gap-4 rounded-2xl border p-4 text-left transition disabled:cursor-default",
                esCorrecta ? "border-ok bg-ok/15" : esElegida && correcta !== null ? "border-bad bg-bad/15"
                  : esElegida ? "border-brand bg-brand/15" : "border-line bg-surface hover:border-brand")}>
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-line text-sm font-bold">{n + 1}</span>
              <span className="flex-1">{o.texto}</span>
              {esCorrecta && <Check className="text-ok" aria-label="Correcta" />}
              {esElegida && !esCorrecta && correcta !== null && <X className="text-bad" aria-label="Incorrecta" />}
            </button>
          );
        })}
      </div>
    </div>
  );
}
