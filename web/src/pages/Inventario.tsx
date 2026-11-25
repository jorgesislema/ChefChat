import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { Search } from "lucide-react";
import { api } from "../lib/api";
import { Badge, Cargando, ErrorCaja, FiltroTipo, Pagina, Pestanas, Tabla, Td, Th, Vacio } from "../components/ui/ui";
import { diasRestantes, etiquetaDias, semaforo } from "../lib/format";
import { Foquito } from "../components/Foquito";
import { TablaLotes } from "../components/edicion/TablaLotes";
import { TablaProductos } from "../components/edicion/TablaProductos";
import { Conteo } from "../components/conteo/Conteo";

const RANGOS = [
  { id: "1", nombre: "Esta semana", p: { semanas: 1 } },
  { id: "2", nombre: "2 semanas", p: { semanas: 2 } },
  { id: "4", nombre: "4 semanas", p: { semanas: 4 } },
  { id: "dic", nombre: "Diciembre", p: { mes: 12 } },
];

function Existencias() {
  const { data, isLoading, error, refetch } = useQuery({ queryKey: ["inventario"], queryFn: api.inventario });
  const [q, setQ] = useState("");
  const [cat, setCat] = useState("");
  const [tipo, setTipo] = useState("");
  const cats = useMemo(() => [...new Set((data?.productos ?? []).map((p) => p.categoria).filter(Boolean))].sort() as string[], [data]);
  if (error) return <ErrorCaja error={error} onReintentar={() => refetch()} />;
  if (isLoading || !data) return <Cargando />;
  const filas = data.productos.filter((p) => (!cat || p.categoria === cat) && (!tipo || p.tipo === tipo) && p.producto.toLowerCase().includes(q.trim().toLowerCase()));
  return (
    <>
      <div className="flex flex-wrap gap-3">
        <div className="relative min-w-60 flex-1">
          <Search size={16} className="absolute left-3 top-3 text-muted" aria-hidden />
          <label className="sr-only" htmlFor="buscar">Buscar producto</label>
          <input id="buscar" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Buscar producto…"
            className="w-full rounded-xl border border-line bg-surface py-2 pl-9 pr-3" />
        </div>
        <label className="sr-only" htmlFor="cat">Categoría</label>
        <select id="cat" value={cat} onChange={(e) => setCat(e.target.value)} className="rounded-xl border border-line bg-surface px-3 py-2">
          <option value="">Todas las categorías</option>
          {cats.map((c) => <option key={c}>{c}</option>)}
        </select>
        <FiltroTipo valor={tipo} onCambia={setTipo} />
      </div>
      {filas.length === 0 ? <Vacio titulo="No encontré productos" texto="Prueba con otro nombre o cambia los filtros." /> : (
        <Tabla>
          <thead><tr><Th>Producto</Th><Th>Categoría</Th><Th className="text-right">Stock</Th><Th>Unidad</Th></tr></thead>
          <tbody>
            {filas.map((p, i) => (
              <tr key={`${p.producto}-${i}`}><Td className="font-medium">{p.producto}</Td><Td>{p.categoria ?? "—"}</Td>
                <Td className="text-right tabular-nums">{p.stock}</Td><Td>{p.unidad}</Td></tr>
            ))}
          </tbody>
        </Tabla>
      )}
    </>
  );
}

function Vencimientos({ rango, onRango }: { rango: string; onRango: (r: string) => void }) {
  const r = RANGOS.find((x) => x.id === rango) ?? RANGOS[0];
  const [tipo, setTipo] = useState("");
  const { data, isLoading, error, refetch } = useQuery({ queryKey: ["venc", r.id], queryFn: () => api.vencimientos(r.p) });
  const lotes = (data?.lotes ?? []).filter((l) => !tipo || l.tipo === tipo);
  return (
    <>
      <div className="flex flex-wrap items-center gap-3">
        <Pestanas valor={r.id} onCambia={onRango} items={RANGOS.map(({ id, nombre }) => ({ id, nombre }))} />
        <FiltroTipo valor={tipo} onCambia={setTipo} />
      </div>
      {error ? <ErrorCaja error={error} onReintentar={() => refetch()} /> : isLoading || !data ? <Cargando /> :
        lotes.length === 0 ? <Vacio titulo="No vence nada en este periodo" texto="Elige otro periodo o cambia el filtro para ver más lotes." /> : (
          <Tabla>
            <thead><tr><Th>Producto</Th><Th>Lote</Th><Th className="text-right">Cantidad</Th><Th>Vence</Th><Th>Estado</Th></tr></thead>
            <tbody>
              {lotes.map((l, i) => {
                const d = diasRestantes(l.vence);
                return (
                  <tr key={`${l.lote}-${i}`}><Td className="font-medium"><span className="flex items-center gap-2">{l.producto}<Foquito dias={d} tipo={l.tipo} /></span></Td><Td>{l.lote}</Td>
                    <Td className="text-right tabular-nums">{l.cantidad} {l.unidad}</Td><Td>{l.vence}</Td>
                    <Td><Badge nivel={semaforo(d)}>{etiquetaDias(d)}</Badge></Td></tr>
                );
              })}
            </tbody>
          </Tabla>
        )}
    </>
  );
}

export default function Inventario() {
  const [sp, setSp] = useSearchParams();
  const v = sp.get("vista");
  const vista = v === "vencimientos" || v === "lotes" || v === "productos" || v === "conteo" ? v : "existencias";
  const rango = sp.get("rango") ?? "1";
  return (
    <Pagina titulo="Inventario" subtitulo="Lo que tienes en el almacén, cuándo vence y a qué precio lo compras.">
      <Pestanas valor={vista} onCambia={(x) => setSp(x === "vencimientos" ? { vista: x, rango } : x === "existencias" ? {} : { vista: x })}
        items={[{ id: "existencias", nombre: "Existencias" }, { id: "vencimientos", nombre: "Vencimientos" }, { id: "lotes", nombre: "Lotes" }, { id: "productos", nombre: "Productos" }, { id: "conteo", nombre: "Conteo" }]} />
      {vista === "existencias" ? <Existencias /> : vista === "vencimientos" ? <Vencimientos rango={rango} onRango={(r) => setSp({ vista, rango: r })} />
        : vista === "lotes" ? <TablaLotes /> : vista === "conteo" ? <Conteo /> : <TablaProductos />}
    </Pagina>
  );
}
