import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api, type Turno as TurnoId } from "../lib/api";
import { Cargando, ErrorCaja, Pagina, Pestanas } from "../components/ui/ui";
import { Confirmar } from "../components/Confirmar";
import { Campo, campo } from "../components/edicion/comun";
import { Editor } from "../components/turno/Editor";
import { Historial } from "../components/turno/Historial";
import { fechaValida, hoyISO } from "../lib/edicion";
import { TURNOS, esTurno, turnoDeAhora } from "../lib/turno";

type Vista = "informe" | "historial";

export default function Turno() {
  const [sp, setSp] = useSearchParams();
  const hoy = hoyISO();
  const f = sp.get("fecha") ?? "";
  const fecha = fechaValida(f) && f <= hoy ? f : hoy;
  const t = sp.get("turno");
  const turno: TurnoId = esTurno(t) ? t : turnoDeAhora();
  const vista: Vista = sp.get("vista") === "historial" ? "historial" : "informe";

  // Cambios sin guardar: lo avisa el editor; aquí se pregunta antes de cambiar de día, turno o pestaña.
  const [sucio, setSucio] = useState(false);
  const [pendiente, setPendiente] = useState<Record<string, string> | null>(null);
  const alSucio = useCallback((s: boolean) => setSucio(s), []);
  const ir = (destino: Record<string, string>) => {
    if (sucio) setPendiente(destino);
    else setSp(destino);
  };
  useEffect(() => {
    if (!sucio) return;
    const f = (e: BeforeUnloadEvent) => { e.preventDefault(); e.returnValue = ""; };
    window.addEventListener("beforeunload", f);
    return () => window.removeEventListener("beforeunload", f);
  }, [sucio]);

  const informe = useQuery({ queryKey: ["informe", fecha, turno], queryFn: () => api.informe(fecha, turno), gcTime: 0, enabled: vista === "informe" });
  const trabajadores = useQuery({ queryKey: ["trabajadores"], queryFn: api.trabajadores, staleTime: 60_000 });
  const recetas = useQuery({ queryKey: ["recetas", "turno"], queryFn: () => api.recetas({}), staleTime: 60_000 });

  return (
    <Pagina titulo="Informe del turno" subtitulo="Lo que pasó en cada turno, para el gerente.">
      <div className="no-print">
        <Pestanas<Vista> valor={vista} onCambia={(v) => ir(v === "historial" ? { vista: "historial" } : { fecha, turno })}
          items={[{ id: "informe", nombre: "Informe" }, { id: "historial", nombre: "Historial" }]} />
      </div>

      {vista === "historial" ? <Historial alAbrir={(fe, tu) => ir({ fecha: fe, turno: tu })} /> : (
        <>
          <div className="no-print flex flex-wrap items-end gap-3">
            <Campo id="turno-fecha" etiqueta="Fecha">
              <input id="turno-fecha" type="date" className={campo} value={fecha} max={hoy}
                onChange={(e) => e.target.value && ir({ fecha: e.target.value, turno })} />
            </Campo>
            <Campo id="turno-turno" etiqueta="Turno">
              <select id="turno-turno" className={campo} value={turno} onChange={(e) => ir({ fecha, turno: e.target.value })}>
                {TURNOS.map((x) => <option key={x.id} value={x.id}>{x.nombre}</option>)}
              </select>
            </Campo>
          </div>
          {informe.isLoading || informe.isFetching && !informe.data ? <Cargando filas={6} />
            : informe.isError ? <ErrorCaja error={informe.error} onReintentar={() => void informe.refetch()} />
            : informe.data && (
              <Editor key={`${fecha}-${turno}`} inicial={informe.data} todos={trabajadores.data?.trabajadores ?? []}
                recetas={recetas.data?.recetas ?? []} alSucio={alSucio} />
            )}
        </>
      )}

      {pendiente && (
        <Confirmar titulo="Hay cambios sin guardar" texto="Tienes cambios sin guardar en este informe. Si sigues, se pierden."
          confirmar="Sí, descartar" deshacer="No se puede deshacer."
          alConfirmar={async () => { setSucio(false); setSp(pendiente); }} alCerrar={() => setPendiente(null)} />
      )}
    </Pagina>
  );
}
