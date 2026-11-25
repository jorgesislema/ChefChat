import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ClipboardList, Plus } from "lucide-react";
import { api, type ConteoResumen } from "../../lib/api";
import { avancePct } from "../../lib/conteo";
import { hoyISO } from "../../lib/edicion";
import { dinero, fechaLarga } from "../../lib/format";
import { Badge, Button, Cargando, ErrorCaja, Tabla, Td, Th, Vacio, cx } from "../ui/ui";
import { Campo, DialogoEdicion, campo } from "../edicion/comun";
import { useRefrescarConteo } from "./refrescar";

function EmpezarDialogo({ onCerrar, alAbrir }: { onCerrar: () => void; alAbrir: (id: number) => void }) {
  const refrescar = useRefrescarConteo();
  const hoy = hoyISO();
  const [fecha, setFecha] = useState(hoy);
  const [limpieza, setLimpieza] = useState(false);
  const [notas, setNotas] = useState("");
  const m = useMutation({
    mutationFn: () => api.crearConteo({ fecha, incluye_limpieza: limpieza, ...(notas.trim() ? { notas: notas.trim() } : {}) }),
    onSuccess: async (r) => { await refrescar(); onCerrar(); alAbrir(r.id); },
  });
  return (
    <DialogoEdicion titulo="Empezar conteo" onCerrar={onCerrar}>
      <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); if (fecha && !m.isPending) m.mutate(); }}>
        <p className="text-sm text-muted">Armo una hoja con lo que el sistema dice que hay de cada producto. Tú anotas lo que realmente cuentas.</p>
        <Campo id="ec-fecha" etiqueta="Fecha del conteo">
          <input id="ec-fecha" type="date" max={hoy} required className={campo} value={fecha} onChange={(e) => setFecha(e.target.value)} />
        </Campo>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={limpieza} onChange={(e) => setLimpieza(e.target.checked)} />
          Contar también productos de limpieza
        </label>
        <Campo id="ec-notas" etiqueta="Notas (opcional)">
          <input id="ec-notas" className={campo} value={notas} onChange={(e) => setNotas(e.target.value)} autoComplete="off" />
        </Campo>
        {m.error != null && <ErrorCaja error={m.error} />}
        <div className="flex justify-end gap-2">
          <Button type="button" onClick={onCerrar}>Cancelar</Button>
          <Button type="submit" variante="primario" disabled={m.isPending || !fecha}>{m.isPending ? "Armando la hoja…" : "Empezar conteo"}</Button>
        </div>
      </form>
    </DialogoEdicion>
  );
}

function FilaConteo({ c, alAbrir }: { c: ConteoResumen; alAbrir: (id: number) => void }) {
  const cerrado = c.estado === "cerrado";
  const dif = cerrado && c.valor_contado !== null && c.valor_sistema !== null ? Math.round((c.valor_contado - c.valor_sistema) * 100) / 100 : null;
  return (
    <tr>
      <Td className="font-medium">
        {fechaLarga(c.fecha)}
        {c.es_demo ? <span className="mt-1 block text-xs font-normal text-muted">Datos de demostración</span> : null}
      </Td>
      <Td><Badge nivel={cerrado ? "ok" : "warn"}>{cerrado ? "Cerrado" : "Abierto"}</Badge></Td>
      <Td className="whitespace-nowrap">{c.n_contadas} de {c.n_lineas} contados <span className="text-muted">({avancePct(c.n_contadas, c.n_lineas)} %)</span></Td>
      <Td className="whitespace-nowrap text-right tabular-nums">{cerrado ? dinero(c.valor_contado) : "—"}</Td>
      <Td className={cx("whitespace-nowrap text-right tabular-nums", dif !== null && dif < 0 && "text-bad", dif !== null && dif > 0 && "text-warn")}>
        {dif === null ? "—" : `${dif > 0 ? "+" : ""}${dinero(dif)}`}
      </Td>
      <Td><Button aria-label={`${cerrado ? "Ver" : "Seguir contando"} el conteo del ${fechaLarga(c.fecha)}`} onClick={() => alAbrir(c.id)}>{cerrado ? "Ver" : "Seguir contando"}</Button></Td>
    </tr>
  );
}

export function ListaConteos({ alAbrir }: { alAbrir: (id: number) => void }) {
  const { data, error, refetch } = useQuery({ queryKey: ["conteos"], queryFn: api.conteos });
  const [nuevo, setNuevo] = useState(false);
  const conteos = data?.conteos ?? [];
  const abierto = conteos.find((c) => c.estado === "abierto");
  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="max-w-xl text-sm text-muted">Haz un conteo el último día de cada mes. Con dos conteos, el costo real de tu comida es exacto.</p>
        {data && (abierto
          ? <Button variante="primario" onClick={() => alAbrir(abierto.id)}><ClipboardList size={16} aria-hidden /> Seguir contando</Button>
          : <Button variante="primario" onClick={() => setNuevo(true)}><Plus size={16} aria-hidden /> Empezar conteo</Button>)}
      </div>
      {error ? <ErrorCaja error={error} onReintentar={() => refetch()} /> : !data ? <Cargando /> :
        conteos.length === 0 ? <Vacio titulo="Aún no has hecho ningún conteo" texto="Usa «Empezar conteo» para armar la hoja con lo que el sistema dice que hay." /> : (
          <Tabla>
            <thead><tr><Th>Fecha</Th><Th>Estado</Th><Th>Avance</Th><Th className="text-right">Valor contado</Th><Th className="text-right">Diferencia</Th><Th><span className="sr-only">Acciones</span></Th></tr></thead>
            <tbody>{conteos.map((c) => <FilaConteo key={c.id} c={c} alAbrir={alAbrir} />)}</tbody>
          </Tabla>
        )}
      {nuevo && <EmpezarDialogo onCerrar={() => setNuevo(false)} alAbrir={alAbrir} />}
    </>
  );
}
