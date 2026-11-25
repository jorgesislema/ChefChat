import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type FilaInforme, type Turno } from "../../lib/api";
import { Badge, Button, Cargando, ErrorCaja, Tabla, Td, Th, Vacio } from "../ui/ui";
import { fechaLarga } from "../../lib/format";
import { hace, nombreTurno } from "../../lib/turno";
import { dinero } from "../../lib/format";

const RANGOS = [{ id: "7", nombre: "Últimos 7 días" }, { id: "30", nombre: "Últimos 30 días" }, { id: "todo", nombre: "Todo" }];

export function Historial({ alAbrir }: { alAbrir: (fecha: string, turno: Turno) => void }) {
  const [rango, setRango] = useState("7");
  const desde = rango === "todo" ? "" : hace(Number(rango));
  const q = useQuery({ queryKey: ["informes", desde], queryFn: () => api.informes({ desde }) });
  const filas: FilaInforme[] = q.data?.informes ?? [];

  return (
    <div className="space-y-4">
      <div role="group" aria-label="Periodo" className="inline-flex flex-wrap gap-1 rounded-xl border border-line bg-surface p-1">
        {RANGOS.map((r) => (
          <button key={r.id} type="button" aria-pressed={rango === r.id} onClick={() => setRango(r.id)}
            className={`rounded-lg px-3 py-1 text-sm font-medium transition ${rango === r.id ? "bg-brand text-black" : "text-muted hover:text-ink"}`}>{r.nombre}</button>
        ))}
      </div>
      {q.isLoading ? <Cargando /> : q.isError ? <ErrorCaja error={q.error} onReintentar={() => void q.refetch()} /> : filas.length === 0 ? (
        <Vacio titulo="No hay informes en este periodo" texto="Cuando el chef guarde o firme un informe de turno, aparecerá aquí. Prueba con un periodo más largo." />
      ) : (
        <Tabla>
          <thead>
            <tr>
              <Th>Fecha</Th><Th>Turno</Th><Th>Chef</Th><Th>Estado</Th><Th className="text-right">Incidencias</Th>
              <Th className="text-right">Producidos</Th><Th className="text-right">Sobrantes</Th><Th className="text-right">Merma</Th><Th><span className="sr-only">Abrir</span></Th>
            </tr>
          </thead>
          <tbody>
            {filas.map((f) => (
              <tr key={f.id}>
                <Td>{fechaLarga(f.fecha)}</Td>
                <Td>{nombreTurno(f.turno)}</Td>
                <Td>{f.chef ?? <span className="text-muted">Sin chef</span>}</Td>
                <Td><Badge nivel={f.estado === "firmado" ? "ok" : "warn"}>{f.estado === "firmado" ? "Firmado" : "Borrador"}</Badge></Td>
                <Td className="text-right">{f.n_incidencias}</Td>
                <Td className="text-right">{f.totales ? f.totales.platos_producidos : "—"}</Td>
                <Td className="text-right">{f.totales ? f.totales.platos_sobrantes : "—"}</Td>
                <Td className="text-right">{f.totales ? dinero(f.totales.merma) : "—"}</Td>
                <Td><Button onClick={() => alAbrir(f.fecha, f.turno)} aria-label={`Abrir el informe del ${fechaLarga(f.fecha)}, turno ${nombreTurno(f.turno)}`}>Abrir</Button></Td>
              </tr>
            ))}
          </tbody>
        </Tabla>
      )}
    </div>
  );
}
