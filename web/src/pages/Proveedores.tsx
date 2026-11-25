import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Phone, Plus, Search, Trash2, TrendingUp } from "lucide-react";
import { api, type NuevoProveedor, type Proveedor, type UnidadPrecio } from "../lib/api";
import { Badge, Button, Card, Cargando, Dialogo, ErrorCaja, FiltroTipo, Pagina, Skeleton, Tabla, Td, Th, Vacio, cx } from "../components/ui/ui";
import { cambioPrecio, precio, precioConUnidad } from "../lib/precios";
import { ConfirmarQuitar, useRefrescar } from "../components/edicion/comun";
import { CambiarPrecioDialogo, EditarProveedorDialogo } from "../components/edicion/ProveedorDialogos";
import type { ProductoProveedor } from "../lib/api";

const campo = "w-full rounded-xl border border-line bg-bg px-3 py-2";
const PORQUE_UNIDAD: Record<UnidadPrecio, string> = { kg: "por kg", l: "por litro", unidad: "por unidad" };

function Etiqueta({ children }: { children: string }) {
  return <span className="rounded-full border border-line px-2 py-0.5 text-xs text-muted">{children}</span>;
}

function Alertas() {
  const q = useQuery({ queryKey: ["alertas-precios"], queryFn: api.alertasPrecios });
  if (!q.data || q.data.alertas.length === 0) return null;
  return (
    <Card role="region" aria-label="Subidas de precio" className="border-warn/40 bg-warn/10">
      <h2 className="mb-2 flex items-center gap-2 font-semibold text-warn"><TrendingUp size={18} aria-hidden /> Subidas de precio</h2>
      <ul className="space-y-1 text-sm">
        {q.data.alertas.map((a, i) => (
          <li key={`${a.producto}-${a.proveedor}-${i}`}>
            <span className="font-medium">{a.producto}</span> ({a.proveedor}) subió {Math.round(a.cambio_pct)} %, de {precio(a.anterior)} a {precio(a.actual)} {PORQUE_UNIDAD[a.unidad_precio]}.
          </li>
        ))}
      </ul>
    </Card>
  );
}

function NuevoProveedorDialogo({ onCerrar, onCreado }: { onCerrar: () => void; onCreado: (id: number) => void }) {
  const qc = useQueryClient();
  const [f, setF] = useState<NuevoProveedor>({ nombre: "", contacto: "", telefono: "", dias_entrega: "", notas: "" });
  const m = useMutation({
    mutationFn: () => api.crearProveedor(Object.fromEntries(Object.entries(f).map(([k, v]) => [k, (v ?? "").trim()])) as unknown as NuevoProveedor),
    onSuccess: async (r) => { await qc.invalidateQueries({ queryKey: ["proveedores"] }); onCreado(r.id); },
  });
  const set = (k: keyof NuevoProveedor) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setF({ ...f, [k]: e.target.value });
  return (
    <Dialogo titulo="Nuevo proveedor" onCerrar={onCerrar}>
      <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); m.mutate(); }}>
        <div><label htmlFor="pv-nombre" className="mb-1 block text-sm font-medium">Nombre del proveedor</label>
          <input id="pv-nombre" required className={campo} value={f.nombre} onChange={set("nombre")} /></div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div><label htmlFor="pv-contacto" className="mb-1 block text-sm font-medium">Persona de contacto</label>
            <input id="pv-contacto" className={campo} value={f.contacto} onChange={set("contacto")} /></div>
          <div><label htmlFor="pv-tel" className="mb-1 block text-sm font-medium">Teléfono</label>
            <input id="pv-tel" type="tel" className={campo} value={f.telefono} onChange={set("telefono")} /></div>
        </div>
        <div><label htmlFor="pv-dias" className="mb-1 block text-sm font-medium">Días de entrega</label>
          <input id="pv-dias" placeholder="Por ejemplo: lunes y jueves" className={campo} value={f.dias_entrega} onChange={set("dias_entrega")} /></div>
        <div><label htmlFor="pv-notas" className="mb-1 block text-sm font-medium">Notas</label>
          <textarea id="pv-notas" rows={2} className={campo} value={f.notas} onChange={set("notas")} /></div>
        {m.error != null && <ErrorCaja error={m.error} />}
        <div className="flex justify-end gap-2">
          <Button type="button" onClick={onCerrar}>Cancelar</Button>
          <Button type="submit" variante="primario" disabled={!f.nombre.trim() || m.isPending}>Guardar proveedor</Button>
        </div>
      </form>
    </Dialogo>
  );
}

function FormularioPrecio({ proveedorId }: { proveedorId: number }) {
  const qc = useQueryClient();
  const cat = useQuery({ queryKey: ["catalogo"], queryFn: api.catalogo });
  const [producto, setProducto] = useState("");
  const [valor, setValor] = useState("");
  const [unidad, setUnidad] = useState<UnidadPrecio>("kg");
  const [categoria, setCategoria] = useState("");
  const [aviso, setAviso] = useState("");
  const nombres = cat.data?.productos ?? [];
  const existe = nombres.some((p) => p.nombre.toLowerCase() === producto.trim().toLowerCase());
  const categorias = useMemo(() => [...new Set(nombres.map((p) => p.categoria).filter(Boolean))].sort() as string[], [nombres]);
  const m = useMutation({
    mutationFn: () => api.guardarPrecio(proveedorId, {
      producto: producto.trim(), precio: Number(valor.replace(",", ".")), unidad_precio: unidad,
      ...(!existe && categoria.trim() ? { categoria: categoria.trim() } : {}),
    }),
    onSuccess: async (r) => {
      setAviso(r.producto_creado ? "Precio guardado. Agregué el producto nuevo a tu lista." : "Precio guardado.");
      setProducto(""); setValor(""); setCategoria("");
      await Promise.all(["proveedor", "proveedores", "alertas-precios", "catalogo"].map((k) => qc.invalidateQueries({ queryKey: [k] })));
    },
  });
  const valido = producto.trim() !== "" && Number(valor.replace(",", ".")) > 0;
  return (
    <Card>
      <h3 className="mb-3 font-semibold">Agregar o cambiar un precio</h3>
      <form className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4" onSubmit={(e) => { e.preventDefault(); setAviso(""); m.mutate(); }}>
        <div className="sm:col-span-2">
          <label htmlFor="pr-producto" className="mb-1 block text-sm font-medium">Producto</label>
          <input id="pr-producto" list="pr-catalogo" className={campo} value={producto} onChange={(e) => { setProducto(e.target.value); setAviso(""); }} autoComplete="off" />
          <datalist id="pr-catalogo">{nombres.map((p) => <option key={p.id} value={p.nombre} />)}</datalist>
        </div>
        <div>
          <label htmlFor="pr-precio" className="mb-1 block text-sm font-medium">Precio ($)</label>
          <input id="pr-precio" inputMode="decimal" className={campo} value={valor} onChange={(e) => setValor(e.target.value)} placeholder="0,00" />
        </div>
        <div>
          <label htmlFor="pr-unidad" className="mb-1 block text-sm font-medium">Se vende por</label>
          <select id="pr-unidad" className={campo} value={unidad} onChange={(e) => setUnidad(e.target.value as UnidadPrecio)}>
            <option value="kg">kg</option><option value="l">litro</option><option value="unidad">unidad</option>
          </select>
        </div>
        {producto.trim() !== "" && !existe && !cat.isLoading && (
          <div className="sm:col-span-2">
            <label htmlFor="pr-categoria" className="mb-1 block text-sm font-medium">Categoría (opcional)</label>
            <input id="pr-categoria" list="pr-categorias" className={campo} value={categoria} onChange={(e) => setCategoria(e.target.value)} autoComplete="off" />
            <datalist id="pr-categorias">{categorias.map((c) => <option key={c} value={c} />)}</datalist>
            <p className="mt-1 text-xs text-muted">Ese producto aún no está en tu lista. Se agregará con este precio.</p>
          </div>
        )}
        <div className="flex items-end sm:col-span-2 lg:col-span-4">
          <Button type="submit" variante="primario" disabled={!valido || m.isPending}>{m.isPending ? "Guardando…" : "Guardar precio"}</Button>
        </div>
      </form>
      <div aria-live="polite" className="mt-3 space-y-2">
        {m.error != null && <ErrorCaja error={m.error} />}
        {aviso && !m.error && <p className="text-sm text-ok">{aviso}</p>}
      </div>
    </Card>
  );
}

function Detalle({ id }: { id: number }) {
  const q = useQuery({ queryKey: ["proveedor", id], queryFn: () => api.proveedor(id) });
  const [busca, setBusca] = useState("");
  const [cat, setCat] = useState("");
  const [tipo, setTipo] = useState("");
  const [dlg, setDlg] = useState<{ tipo: "editar" | "quitar" } | { tipo: "precio" | "producto"; x: ProductoProveedor } | null>(null);
  const qc = useQueryClient();
  const refrescar = useRefrescar();
  const productos = q.data?.productos ?? [];
  const cats = useMemo(() => [...new Set(productos.map((p) => p.categoria).filter(Boolean))].sort() as string[], [productos]);
  if (q.error) return <ErrorCaja error={q.error} onReintentar={() => q.refetch()} />;
  if (!q.data) return <Cargando filas={5} />;
  const { proveedor: p } = q.data;
  const filas = productos.filter((x) => (!cat || x.categoria === cat) && (!tipo || x.tipo === tipo)
    && x.producto.toLowerCase().includes(busca.trim().toLowerCase()));
  return (
    <div className="space-y-4">
      <Card>
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-xl font-semibold">{p.nombre}</h2>
          {p.es_demo === 1 && <Etiqueta>Datos de demostración</Etiqueta>}
          <div className="ml-auto flex gap-2">
            <Button onClick={() => setDlg({ tipo: "editar" })}><Pencil size={14} aria-hidden /> Editar datos</Button>
            <Button variante="peligro" onClick={() => setDlg({ tipo: "quitar" })}><Trash2 size={14} aria-hidden /> Quitar proveedor</Button>
          </div>
        </div>
        <dl className="mt-3 grid gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
          <div><dt className="text-muted">Contacto</dt><dd>{p.contacto || "—"}</dd></div>
          <div><dt className="text-muted">Teléfono</dt><dd className="flex items-center gap-1">{p.telefono ? <><Phone size={14} aria-hidden />{p.telefono}</> : "—"}</dd></div>
          <div><dt className="text-muted">Días de entrega</dt><dd>{p.dias_entrega || "—"}</dd></div>
          <div><dt className="text-muted">Notas</dt><dd>{p.notas || "—"}</dd></div>
        </dl>
      </Card>

      <div className="flex flex-wrap gap-3">
        <div className="relative min-w-52 flex-1">
          <Search size={16} className="absolute left-3 top-3 text-muted" aria-hidden />
          <label className="sr-only" htmlFor="pv-buscar">Buscar producto</label>
          <input id="pv-buscar" value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Buscar producto…" className="w-full rounded-xl border border-line bg-surface py-2 pl-9 pr-3" />
        </div>
        <label className="sr-only" htmlFor="pv-cat">Categoría</label>
        <select id="pv-cat" value={cat} onChange={(e) => setCat(e.target.value)} className="rounded-xl border border-line bg-surface px-3 py-2">
          <option value="">Todas las categorías</option>
          {cats.map((c) => <option key={c}>{c}</option>)}
        </select>
        <FiltroTipo valor={tipo} onCambia={setTipo} />
      </div>

      {productos.length === 0 ? (
        <Vacio titulo="Este proveedor aún no tiene precios" texto="Usa el formulario de abajo para agregar el primer precio." />
      ) : filas.length === 0 ? (
        <Vacio titulo="No encontré productos" texto="Prueba con otro nombre o cambia los filtros." />
      ) : (
        <Tabla>
          <thead><tr><Th>Producto</Th><Th>Categoría</Th><Th>Precio</Th><Th className="hidden 2xl:table-cell">Fecha</Th><Th>Cambio</Th><Th>Comparación</Th><Th><span className="sr-only">Acciones</span></Th></tr></thead>
          <tbody>
            {filas.map((x) => {
              const c = cambioPrecio(x.cambio_pct);
              return (
                <tr key={x.producto_id}>
                  <Td className="font-medium">{x.producto}</Td>
                  <Td>{x.categoria ?? "—"}</Td>
                  <Td className="whitespace-nowrap tabular-nums">{precioConUnidad(x.precio, x.unidad_precio)}</Td>
                  <Td className="hidden whitespace-nowrap 2xl:table-cell">{x.fecha}</Td>
                  <Td className={cx("whitespace-nowrap tabular-nums", c?.nivel === "bad" && "text-bad", c?.nivel === "ok" && "text-ok")}>
                    {c ? <><span aria-hidden>{c.flecha} </span>{c.texto}<span className="sr-only">{c.nivel === "bad" ? " (subió)" : c.nivel === "ok" ? " (bajó)" : " (sin cambio)"}</span></> : <span className="text-muted">—</span>}
                  </Td>
                  <Td className="min-w-40">
                    {x.es_mas_barato ? <span className="whitespace-nowrap"><Badge nivel="ok">Más barato</Badge></span>
                      : x.mejor_proveedor && x.mejor_precio !== null
                        ? <span className="text-xs text-muted">Más barato: {x.mejor_proveedor} a {precioConUnidad(x.mejor_precio, x.unidad_precio)}</span>
                        : <span className="text-muted">—</span>}
                  </Td>
                  <Td>
                    <div className="flex gap-2">
                      <Button aria-label={`Cambiar precio de ${x.producto}`} onClick={() => setDlg({ tipo: "precio", x })}>Cambiar precio</Button>
                      <Button variante="peligro" aria-label={`Quitar ${x.producto} de ${p.nombre}`} onClick={() => setDlg({ tipo: "producto", x })}>Quitar</Button>
                    </div>
                  </Td>
                </tr>
              );
            })}
          </tbody>
        </Tabla>
      )}
      <FormularioPrecio proveedorId={id} />
      {dlg?.tipo === "editar" && <EditarProveedorDialogo proveedor={p} onCerrar={() => setDlg(null)} />}
      {dlg?.tipo === "precio" && <CambiarPrecioDialogo proveedorId={id} proveedor={p.nombre} producto={dlg.x.producto} precio={dlg.x.precio} unidad={dlg.x.unidad_precio} onCerrar={() => setDlg(null)} />}
      {dlg?.tipo === "quitar" && (
        <ConfirmarQuitar titulo={`Quitar a ${p.nombre}`} confirmar="Sí, quitar proveedor" alCerrar={() => setDlg(null)}
          texto="Dejarás de ver a este proveedor. Sus precios quedan guardados."
          alConfirmar={async () => { await api.quitarProveedor(id); await qc.invalidateQueries({ queryKey: ["proveedores"] }); await refrescar(); }} />
      )}
      {dlg?.tipo === "producto" && (
        <ConfirmarQuitar titulo={`Quitar ${dlg.x.producto}`} confirmar="Sí, quitar" alCerrar={() => setDlg(null)}
          texto={`${p.nombre} ya no vende ${dlg.x.producto}. El historial de precios se conserva.`}
          alConfirmar={async () => { await api.quitarProductoDeProveedor(id, dlg.x.producto_id); await refrescar(); }} />
      )}
    </div>
  );
}

function Lista({ proveedores, elegido, onElige }: { proveedores: Proveedor[]; elegido: number | null; onElige: (id: number) => void }) {
  return (
    <ul className="space-y-2" aria-label="Lista de proveedores">
      {proveedores.map((p) => (
        <li key={p.id}>
          <button onClick={() => onElige(p.id)} aria-current={p.id === elegido ? "true" : undefined}
            className={cx("w-full rounded-2xl border p-4 text-left transition hover:bg-line/40", p.id === elegido ? "border-brand bg-brand/10" : "border-line bg-surface")}>
            <span className="block font-semibold">{p.nombre}</span>
            <span className="mt-0.5 block text-sm text-muted">{p.dias_entrega ? `Entrega: ${p.dias_entrega}` : "Sin días de entrega"}</span>
            <span className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted">
              {p.n_productos ?? 0} {p.n_productos === 1 ? "producto" : "productos"}
              {p.es_demo === 1 && <Etiqueta>Datos de demostración</Etiqueta>}
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}

export default function Proveedores() {
  const q = useQuery({ queryKey: ["proveedores"], queryFn: api.proveedores });
  const [elegido, setElegido] = useState<number | null>(null);
  const [nuevo, setNuevo] = useState(false);
  const lista = q.data?.proveedores ?? [];
  const actual = elegido !== null && lista.some((p) => p.id === elegido) ? elegido : (lista[0]?.id ?? null);
  return (
    <Pagina titulo="Proveedores" subtitulo="Quién te vende qué, a qué precio, y dónde te sale más barato.">
      <Alertas />
      {q.error ? <ErrorCaja error={q.error} onReintentar={() => q.refetch()} /> : !q.data ? (
        <div className="grid gap-6 lg:grid-cols-[18rem_1fr]" role="status" aria-label="Cargando">
          <div className="space-y-2"><Skeleton className="h-20 w-full" /><Skeleton className="h-20 w-full" /><Skeleton className="h-20 w-full" /></div>
          <div className="space-y-3"><Skeleton className="h-32 w-full" /><Skeleton className="h-48 w-full" /></div>
        </div>
      ) : lista.length === 0 ? (
        <>
          <Vacio titulo="Aún no tienes proveedores" texto="Agrega tu primer proveedor y luego anota los precios de lo que te vende. Así sabrás dónde comprar más barato." />
          <div className="flex justify-center"><Button variante="primario" onClick={() => setNuevo(true)}><Plus size={16} aria-hidden /> Nuevo proveedor</Button></div>
        </>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[18rem_1fr]">
          <div className="space-y-3">
            <Button variante="primario" className="w-full" onClick={() => setNuevo(true)}><Plus size={16} aria-hidden /> Nuevo proveedor</Button>
            <Lista proveedores={lista} elegido={actual} onElige={setElegido} />
          </div>
          <div className="min-w-0">{actual !== null && <Detalle key={actual} id={actual} />}</div>
        </div>
      )}
      {nuevo && <NuevoProveedorDialogo onCerrar={() => setNuevo(false)} onCreado={(id) => { setElegido(id); setNuevo(false); }} />}
    </Pagina>
  );
}
