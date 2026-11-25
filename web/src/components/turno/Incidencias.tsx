import { Plus, Trash2 } from "lucide-react";
import { Button, Card } from "../ui/ui";
import { campo } from "../edicion/comun";
import { MAX_OBSERVACIONES } from "../../lib/turno";
import type { IncidenciaTurno } from "../../lib/api";

interface Props {
  incidencias: IncidenciaTurno[];
  tipos: string[];
  observaciones: string;
  soloLectura: boolean;
  alIncidencias: (i: IncidenciaTurno[]) => void;
  alObservaciones: (t: string) => void;
}

export function Incidencias({ incidencias, tipos, observaciones, soloLectura, alIncidencias, alObservaciones }: Props) {
  const cambiar = (i: number, parte: Partial<IncidenciaTurno>) => alIncidencias(incidencias.map((x, k) => (k === i ? { ...x, ...parte } : x)));
  return (
    <Card className="space-y-4">
      <h2 className="text-lg font-semibold">Incidencias del turno</h2>
      {incidencias.length === 0 && <p className="text-sm text-muted">{soloLectura ? "No se anotó ninguna incidencia." : "Sin incidencias. Agrega una si pasó algo que el gerente deba saber."}</p>}
      <ul className="space-y-2">
        {incidencias.map((inc, i) => (
          <li key={i} className="flex flex-wrap items-start gap-2">
            {soloLectura ? <p><strong>{inc.tipo}</strong>: {inc.descripcion}</p> : (
              <>
                <select className={`${campo} w-auto`} aria-label={`Tipo de la incidencia ${i + 1}`} value={inc.tipo} onChange={(e) => cambiar(i, { tipo: e.target.value })}>
                  {(tipos.includes(inc.tipo) ? tipos : [inc.tipo, ...tipos]).map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
                <input className={`${campo} min-w-0 flex-1`} aria-label={`Descripción de la incidencia ${i + 1}`} placeholder="¿Qué pasó?"
                  value={inc.descripcion} onChange={(e) => cambiar(i, { descripcion: e.target.value })} />
                <button type="button" aria-label={`Quitar la incidencia ${i + 1}`} className="rounded-lg p-2 text-bad hover:bg-bad/10"
                  onClick={() => alIncidencias(incidencias.filter((_, k) => k !== i))}><Trash2 size={16} aria-hidden /></button>
              </>
            )}
          </li>
        ))}
      </ul>
      {!soloLectura && (
        <Button type="button" className="no-print" onClick={() => alIncidencias([...incidencias, { tipo: tipos[0] ?? "otro", descripcion: "" }])}>
          <Plus size={14} aria-hidden /> Agregar incidencia
        </Button>
      )}
      <div>
        <label htmlFor="observaciones" className="mb-1 block text-sm font-medium">Observaciones</label>
        {soloLectura ? <p className="whitespace-pre-wrap">{observaciones || "Sin observaciones."}</p> : (
          <>
            <textarea id="observaciones" rows={3} maxLength={MAX_OBSERVACIONES} className={campo} value={observaciones}
              aria-describedby="observaciones-cuenta" onChange={(e) => alObservaciones(e.target.value)} />
            <p id="observaciones-cuenta" className="mt-1 text-right text-xs text-muted">{observaciones.length} / {MAX_OBSERVACIONES}</p>
          </>
        )}
      </div>
    </Card>
  );
}
