import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { api, type Compra } from "../lib/api";
import { atajosCompras } from "../lib/compras";
import { dinero } from "../lib/format";
import { Badge, Button, Card, ErrorCaja, Pagina, Skeleton, Vacio, cx } from "../components/ui/ui";
import { BarrasHorizontales, Dato } from "../components/analisis/Graficos";
import { ConfirmarQuitar, campo } from "../components/edicion/comun";
import { RegistrarCompraDialogo } from "../components/compras/RegistrarCompra";
import { TablaCompras } from "../components/compras/TablaCompras";
import { useRefrescarCompras } from "../components/compras/refrescar";

export default function Compras() {
  const atajos = useMemo(() => atajosCompras(new Date()), []);
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [proveedor, setProveedor] = useState("");
  const [registrando, setRegistrando] = useState(false);
  const [anulando, setAnulando] = useState<Compra | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const refrescar = useRefrescarCompras();
  const mal = desde !== "" && hasta !== "" && desde > hasta;
  const provs = useQuery({ queryKey: ["proveedores"], queryFn: api.proveedores });
  const q = useQuery({
    queryKey: ["compras", desde, hasta, proveedor],
    queryFn: () => api.compras({ desde, hasta, proveedor_id: Number(proveedor) || undefined }),
    enabled: !mal,
    placeholderData: (p) => p,
  });
  const d = q.data;

  return (
    <Pagina titulo="Compras" subtitulo="Lo que compras a tus proveedores y cuánto gastas."
      accion={<Button variante="primario" onClick={() => setRegistrando(true)}><Plus size={16} aria-hidden /> Registrar compra</Button>}>
      <div className="flex flex-wrap items-end gap-4 rounded-2xl border border-line bg-surface p-4">
        <div><label htmlFor="co-desde" className="mb-1 block text-sm text-muted">Desde</label>
          <input id="co-desde" type="date" value={desde} max={hasta || undefined} onChange={(e) => setDesde(e.target.value)} className={cx(campo, "w-auto")} /></div>
        <div><label htmlFor="co-hasta" className="mb-1 block text-sm text-muted">Hasta</label>
          <input id="co-hasta" type="date" value={hasta} min={desde || undefined} onChange={(e) => setHasta(e.target.value)} className={cx(campo, "w-auto")} /></div>
        <div><label htmlFor="co-prov" className="mb-1 block text-sm text-muted">Proveedor</label>
          <select id="co-prov" value={proveedor} onChange={(e) => setProveedor(e.target.value)} className={cx(campo, "w-auto")}>
            <option value="">Todos</option>
            {provs.data?.proveedores.map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}
          </select></div>
        <div role="group" aria-label="Atajos de fechas" className="flex flex-wrap gap-2">
          {atajos.map((a) => {
            const activo = desde === a.desde && hasta === a.hasta;
            return (
              <Button key={a.id} type="button" aria-pressed={activo} className={cx(activo && "border-brand text-brand")}
                onClick={() => { setDesde(a.desde); setHasta(a.hasta); }}>{a.nombre}</Button>
            );
          })}
        </div>
        {mal && <p role="alert" className="w-full text-sm text-bad">La fecha «Desde» no puede ser después de «Hasta».</p>}
      </div>

      {aviso && (
        <div role="status" className="flex flex-wrap items-start justify-between gap-3 rounded-xl border border-warn/40 bg-warn/10 p-3 text-sm">
          <p>{aviso}</p>
          <Button type="button" onClick={() => setAviso(null)}>Entendido</Button>
        </div>
      )}

      {q.error ? <ErrorCaja error={q.error} onReintentar={() => void q.refetch()} /> : !d ? (
        mal ? null : (
          <div className="space-y-4" role="status" aria-label="Cargando las compras">
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-20" />)}</div>
            <Skeleton className="h-64 w-full" />
          </div>
        )
      ) : (
        <div className={cx("space-y-6", q.isFetching && "opacity-60")} aria-busy={q.isFetching}>
          {d.demo && <Badge nivel="warn">Datos de demostración</Badge>}
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Dato etiqueta="Total comprado" valor={dinero(d.total)} />
            <Dato etiqueta="Alimentos" valor={dinero(d.total_alimentos)} />
            <Dato etiqueta="Limpieza" valor={dinero(d.total_limpieza)} />
            <Dato etiqueta="Compras" valor={d.n} />
          </div>
          {d.compras.length === 0 ? (
            <Vacio titulo="No hay compras en estas fechas"
              texto="Prueba con otras fechas o toca «Todo». Para anotar una compra usa el botón «Registrar compra»." />
          ) : (
            <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_18rem]">
              <TablaCompras compras={d.compras} onAnular={setAnulando} />
              <Card className="h-fit">
                <BarrasHorizontales titulo="Gasto por proveedor"
                  filas={d.por_proveedor.map((p) => ({ clave: p.proveedor, etiqueta: p.proveedor, valor: p.total, detalle: dinero(p.total) }))} />
              </Card>
            </div>
          )}
        </div>
      )}

      {registrando && <RegistrarCompraDialogo onCerrar={() => setRegistrando(false)} />}
      {anulando && (
        <ConfirmarQuitar titulo="Anular compra" confirmar="Sí, anular"
          texto="Quitar esta compra. Si su lote no se ha usado, también se quita del inventario."
          alConfirmar={async () => {
            const r = await api.anularCompra(anulando.id);
            setAviso(r.aviso ?? (r.lote_quitado ? "Compra anulada. Su lote se quitó del inventario." : "Compra anulada."));
            await refrescar();
          }}
          alCerrar={() => setAnulando(null)} />
      )}
    </Pagina>
  );
}
