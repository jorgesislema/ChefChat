import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Plus, Search } from "lucide-react";
import { api, type LoteInv } from "../../lib/api";
import { diasRestantes, etiquetaDias, semaforo } from "../../lib/format";
import { Foquito } from "../Foquito";
import { Badge, Button, Cargando, ErrorCaja, FiltroTipo, Tabla, Td, Th, Vacio } from "../ui/ui";
import { ConfirmarQuitar, useRefrescar } from "./comun";
import { AgregarLoteDialogo, EditarLoteDialogo } from "./LoteDialogos";

type Dialogo = { tipo: "agregar" } | { tipo: "editar" | "quitar"; lote: LoteInv } | null;

export function TablaLotes() {
  const refrescar = useRefrescar();
  const { data, error, refetch } = useQuery({ queryKey: ["lotes-inv"], queryFn: () => api.lotes() });
  const [q, setQ] = useState("");
  const [tipo, setTipo] = useState("");
  const [dlg, setDlg] = useState<Dialogo>(null);
  const filas = (data?.lotes ?? []).filter((l) => (!tipo || l.tipo === tipo)
    && `${l.producto} ${l.lote ?? ""}`.toLowerCase().includes(q.trim().toLowerCase()));
  return (
    <>
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative min-w-60 flex-1">
          <Search size={16} className="absolute left-3 top-3 text-muted" aria-hidden />
          <label className="sr-only" htmlFor="lotes-buscar">Buscar lote o producto</label>
          <input id="lotes-buscar" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Buscar producto o código de lote…"
            className="w-full rounded-xl border border-line bg-surface py-2 pl-9 pr-3 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand" />
        </div>
        <FiltroTipo valor={tipo} onCambia={setTipo} />
        <Button variante="primario" onClick={() => setDlg({ tipo: "agregar" })}><Plus size={16} aria-hidden /> Agregar lote</Button>
      </div>
      {error ? <ErrorCaja error={error} onReintentar={() => refetch()} /> : !data ? <Cargando /> :
        data.lotes.length === 0 ? <Vacio titulo="Aún no hay lotes" texto="Usa «Agregar lote» para anotar lo que llega al almacén." /> :
        filas.length === 0 ? <Vacio titulo="No encontré lotes" texto="Prueba con otro nombre o cambia el filtro." /> : (
          <Tabla>
            <thead><tr><Th>Producto</Th><Th>Lote</Th><Th className="text-right">Cantidad</Th><Th>Ingreso</Th><Th>Vence</Th><Th>Tipo</Th><Th><span className="sr-only">Acciones</span></Th></tr></thead>
            <tbody>
              {filas.map((l) => {
                const d = diasRestantes(l.vence);
                return (
                  <tr key={l.id}>
                    <Td className="font-medium"><span className="flex items-center gap-2">{l.producto}<Foquito dias={d} tipo={l.tipo} /></span></Td>
                    <Td>{l.lote ?? "—"}</Td>
                    <Td className="whitespace-nowrap text-right tabular-nums">{l.cantidad} {l.unidad}</Td>
                    <Td className="whitespace-nowrap">{l.fecha_ingreso}</Td>
                    <Td><span className="block whitespace-nowrap">{l.vence}</span><Badge nivel={semaforo(d)}>{etiquetaDias(d)}</Badge></Td>
                    <Td>{l.tipo === "limpieza" ? "Limpieza" : "Alimento"}</Td>
                    <Td>
                      <div className="flex gap-2">
                        <Button aria-label={`Editar lote ${l.lote ?? ""} de ${l.producto}`} onClick={() => setDlg({ tipo: "editar", lote: l })}>Editar</Button>
                        <Button variante="peligro" aria-label={`Quitar lote ${l.lote ?? ""} de ${l.producto}`} onClick={() => setDlg({ tipo: "quitar", lote: l })}>Quitar</Button>
                      </div>
                    </Td>
                  </tr>
                );
              })}
            </tbody>
          </Tabla>
        )}
      {dlg?.tipo === "agregar" && <AgregarLoteDialogo onCerrar={() => setDlg(null)} />}
      {dlg?.tipo === "editar" && <EditarLoteDialogo lote={dlg.lote} onCerrar={() => setDlg(null)} />}
      {dlg?.tipo === "quitar" && (
        <ConfirmarQuitar titulo={`Quitar lote de ${dlg.lote.producto}`} confirmar="Sí, quitar" alCerrar={() => setDlg(null)}
          texto="Sacar este lote del inventario. Úsalo si se acabó, se botó o fue un error de registro."
          deshacer="Queda anotado en el registro de cambios; para recuperarlo hay que volver a agregarlo."
          alConfirmar={async () => { await api.quitarLote(dlg.lote.id); await refrescar(); }} />
      )}
    </>
  );
}
