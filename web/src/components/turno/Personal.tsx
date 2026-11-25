import { useState } from "react";
import { Plus } from "lucide-react";
import { Button, Card } from "../ui/ui";
import { Campo, campo } from "../edicion/comun";
import { fechaLarga } from "../../lib/format";
import { fechaValida } from "../../lib/edicion";
import type { DatosTurno, PersonaTurno, Trabajador } from "../../lib/api";

interface Props {
  datos: DatosTurno["personal"];
  chefs: PersonaTurno[];
  /** Todo el personal, para sumar a alguien de otro turno y para ver nombres. */
  todos: Trabajador[];
  personal: string[];
  chefId: string;
  soloLectura: boolean;
  nombre: (id: string) => string;
  alPersonal: (ids: string[]) => void;
  alChef: (id: string) => void;
}

export function Personal({ datos, chefs, todos, personal, chefId, soloLectura, nombre, alPersonal, alChef }: Props) {
  const [otro, setOtro] = useState("");
  // Quienes trabajan según el servidor, más los que el chef sumó o ya estaban guardados.
  const lista = [...datos.trabajan.map((p) => p.id_empleado), ...personal.filter((id) => !datos.trabajan.some((p) => p.id_empleado === id))];
  const visibles = soloLectura ? personal : lista;
  const disponibles = todos.filter((t) => !lista.includes(t.id_empleado));

  const alternar = (id: string, marcado: boolean) => alPersonal(marcado ? [...personal, id] : personal.filter((x) => x !== id));
  const agregar = () => {
    if (!otro) return;
    alPersonal([...personal, otro]);
    setOtro("");
  };
  const chefOpciones = chefs.some((c) => c.id_empleado === chefId) || !chefId ? chefs : [...chefs, { id_empleado: chefId, nombre: nombre(chefId), cargo: null }];

  return (
    <Card className="space-y-4">
      <h2 className="text-lg font-semibold">Personal del turno</h2>
      <Campo id="chef" etiqueta="Chef del turno" className="max-w-sm">
        {soloLectura ? <p className="py-2">{chefId ? nombre(chefId) : "Sin chef"}</p> : (
          <select id="chef" className={campo} value={chefId} onChange={(e) => alChef(e.target.value)}>
            <option value="">Elige al chef…</option>
            {chefOpciones.map((c) => <option key={c.id_empleado} value={c.id_empleado}>{c.nombre}</option>)}
          </select>
        )}
      </Campo>
      <fieldset>
        <legend className="mb-1 text-sm font-medium">Trabajaron en este turno</legend>
        {visibles.length === 0 ? <p className="text-sm text-muted">No hay nadie marcado.</p> : (
          <ul className="grid gap-1 sm:grid-cols-2 lg:grid-cols-3">
            {visibles.map((id) => (
              <li key={id}>
                <label className="flex min-h-9 items-center gap-2">
                  <input type="checkbox" className="h-5 w-5 accent-[#F5A31A]" checked={personal.includes(id)} disabled={soloLectura}
                    onChange={(e) => alternar(id, e.target.checked)} />
                  <span>{nombre(id)}</span>
                </label>
              </li>
            ))}
          </ul>
        )}
      </fieldset>
      {!soloLectura && (
        <div className="no-print flex flex-wrap items-end gap-2">
          <Campo id="otro-turno" etiqueta="Agregar a alguien de otro turno" className="min-w-0 flex-1 sm:max-w-sm">
            <select id="otro-turno" className={campo} value={otro} onChange={(e) => setOtro(e.target.value)}>
              <option value="">Elige a la persona…</option>
              {disponibles.map((t) => <option key={t.id_empleado} value={t.id_empleado}>{t.nombre_completo}{t.turno ? ` (${t.turno})` : ""}</option>)}
            </select>
          </Campo>
          <Button type="button" onClick={agregar} disabled={!otro}><Plus size={14} aria-hidden /> Agregar</Button>
        </div>
      )}
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <h3 className="mb-1 text-sm font-medium">Descansan hoy</h3>
          {datos.descansan.length === 0 ? <p className="text-sm text-muted">Nadie.</p> : (
            <ul className="text-sm">{datos.descansan.map((p) => <li key={p.id_empleado}>{p.nombre}{p.cargo ? <span className="text-muted"> · {p.cargo}</span> : null}</li>)}</ul>
          )}
        </div>
        <div>
          <h3 className="mb-1 text-sm font-medium">Ausentes</h3>
          {datos.ausentes.length === 0 ? <p className="text-sm text-muted">Nadie.</p> : (
            <ul className="space-y-1 text-sm">
              {datos.ausentes.map((p) => (
                <li key={p.id_empleado}>{p.nombre}: {p.motivo}{p.hasta ? <span className="text-muted"> (hasta el {fechaValida(p.hasta) ? fechaLarga(p.hasta) : p.hasta})</span> : null}</li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </Card>
  );
}
