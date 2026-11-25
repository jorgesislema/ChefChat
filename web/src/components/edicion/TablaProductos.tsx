import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { api, type ProductoCat } from "../../lib/api";
import { precio } from "../../lib/precios";
import { Button, Cargando, ErrorCaja, FiltroTipo, Tabla, Td, Th, Vacio, cx } from "../ui/ui";
import { ConfirmarQuitar, useRefrescar } from "./comun";
import { EditarProductoDialogo, PreciosProductoDialogo } from "./ProductoDialogos";

type Dialogo = { tipo: "editar" | "precios" | "quitar"; p: ProductoCat } | null;

const sinClasificar = (p: ProductoCat) => !p.categoria || p.categoria.trim().toLowerCase() === "sin clasificar";
const POR_UNIDAD: Record<string, string> = { kg: "kg", l: "litro", unidad: "unidad" };

export function TablaProductos() {
  const refrescar = useRefrescar();
  const { data, error, refetch } = useQuery({ queryKey: ["productos-inv"], queryFn: () => api.productosInv() });
  const [q, setQ] = useState("");
  const [cat, setCat] = useState("");
  const [tipo, setTipo] = useState("");
  const [soloSin, setSoloSin] = useState(false);
  const [dlg, setDlg] = useState<Dialogo>(null);
  const todos = data?.productos ?? [];
  const nSin = useMemo(() => todos.filter(sinClasificar).length, [todos]);
  const filas = todos.filter((p) => (!cat || p.categoria === cat) && (!tipo || p.tipo === tipo) && (!soloSin || sinClasificar(p))
    && p.nombre.toLowerCase().includes(q.trim().toLowerCase()));
  return (
    <>
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative min-w-60 flex-1">
          <Search size={16} className="absolute left-3 top-3 text-muted" aria-hidden />
          <label className="sr-only" htmlFor="prod-buscar">Buscar producto</label>
          <input id="prod-buscar" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Buscar producto…"
            className="w-full rounded-xl border border-line bg-surface py-2 pl-9 pr-3 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand" />
        </div>
        <label className="sr-only" htmlFor="prod-cat">Categoría</label>
        <select id="prod-cat" value={cat} onChange={(e) => setCat(e.target.value)} className="rounded-xl border border-line bg-surface px-3 py-2">
          <option value="">Todas las categorías</option>
          {(data?.categorias ?? []).map((c) => <option key={c}>{c}</option>)}
        </select>
        <FiltroTipo valor={tipo} onCambia={setTipo} />
        <button type="button" aria-pressed={soloSin} onClick={() => setSoloSin(!soloSin)}
          className={cx("rounded-full border px-3 py-1.5 text-sm font-medium transition", soloSin ? "border-brand bg-brand text-black" : "border-line text-muted hover:text-ink")}>
          Sin clasificar{data ? ` (${nSin})` : ""}
        </button>
      </div>
      {error ? <ErrorCaja error={error} onReintentar={() => refetch()} /> : !data ? <Cargando /> :
        todos.length === 0 ? <Vacio titulo="Aún no hay productos" texto="Los productos aparecen cuando agregas un lote o un precio de proveedor." /> :
        filas.length === 0 ? <Vacio titulo="No encontré productos" texto="Prueba con otro nombre o cambia los filtros." /> : (
          <Tabla>
            <thead><tr><Th>Producto</Th><Th>Categoría</Th><Th>Tipo</Th><Th className="text-right">Stock</Th><Th className="text-right">Vida útil</Th><Th className="text-right">Proveedores</Th><Th>Más barato</Th><Th><span className="sr-only">Acciones</span></Th></tr></thead>
            <tbody>
              {filas.map((p) => (
                <tr key={p.id}>
                  <Td className="font-medium">{p.nombre}</Td>
                  <Td>{p.categoria ?? "—"}</Td>
                  <Td>{p.tipo === "limpieza" ? "Limpieza" : "Alimento"}</Td>
                  <Td className="whitespace-nowrap text-right tabular-nums">{p.stock} {p.unidad_stock ?? ""}</Td>
                  <Td className="whitespace-nowrap text-right tabular-nums">{p.vida_util_dias === null ? "—" : `${p.vida_util_dias} días`}</Td>
                  <Td className="text-right tabular-nums">{p.n_proveedores}</Td>
                  <Td className="min-w-40">
                    {p.mejor_precio === null ? <span className="text-muted">—</span>
                      : <span>{precio(p.mejor_precio)}{p.mejor_unidad ? ` por ${POR_UNIDAD[p.mejor_unidad] ?? p.mejor_unidad}` : ""}{p.mejor_proveedor ? ` · ${p.mejor_proveedor}` : ""}</span>}
                  </Td>
                  <Td>
                    <div className="flex gap-2">
                      <Button aria-label={`Editar ${p.nombre}`} onClick={() => setDlg({ tipo: "editar", p })}>Editar</Button>
                      <Button aria-label={`Ver precios de ${p.nombre}`} onClick={() => setDlg({ tipo: "precios", p })}>Precios</Button>
                      <Button variante="peligro" aria-label={`Quitar ${p.nombre}`} onClick={() => setDlg({ tipo: "quitar", p })}>Quitar</Button>
                    </div>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Tabla>
        )}
      {dlg?.tipo === "editar" && <EditarProductoDialogo producto={dlg.p} categorias={data?.categorias ?? []} onCerrar={() => setDlg(null)} />}
      {dlg?.tipo === "precios" && <PreciosProductoDialogo producto={dlg.p} onCerrar={() => setDlg(null)} />}
      {dlg?.tipo === "quitar" && (
        <ConfirmarQuitar titulo={`Quitar ${dlg.p.nombre}`} confirmar="Sí, quitar" alCerrar={() => setDlg(null)}
          texto={`Quitar «${dlg.p.nombre}» de tu lista de productos. Solo se puede si no tiene lotes, precios ni recetas que lo usen.`}
          deshacer="Si algo lo usa, el programa te dirá qué es y no se quitará nada."
          alConfirmar={async () => { await api.quitarProducto(dlg.p.id); await refrescar(); }} />
      )}
    </>
  );
}
