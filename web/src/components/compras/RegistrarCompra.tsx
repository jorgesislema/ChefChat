import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { CheckCircle2 } from "lucide-react";
import { api, type UnidadPrecio } from "../../lib/api";
import { UNIDADES_CANTIDAD, UNIDADES_PRECIO, totalCompra } from "../../lib/compras";
import { aNumero, hoyISO } from "../../lib/edicion";
import { dinero } from "../../lib/format";
import { precioConUnidad } from "../../lib/precios";
import { Button, ErrorCaja } from "../ui/ui";
import { Avisos, Campo, DialogoEdicion, campo } from "../edicion/comun";
import { useRefrescarCompras } from "./refrescar";

const NOMBRE_PRECIO: Record<UnidadPrecio, string> = { kg: "kg", l: "litros", unidad: "unidades" };

interface Guardada { total: number; lote: string | null; productoCreado: boolean }

/** Diálogo para anotar una compra. Muestra el total calculado antes de guardar y el que devuelve el servidor después. */
export function RegistrarCompraDialogo({ onCerrar }: { onCerrar: () => void }) {
  const refrescar = useRefrescarCompras();
  const hoy = useMemo(() => hoyISO(), []);
  const provs = useQuery({ queryKey: ["proveedores"], queryFn: api.proveedores });
  const cat = useQuery({ queryKey: ["catalogo"], queryFn: api.catalogo });
  const [f, setF] = useState({
    proveedor: "", producto: "", cantidad: "", unidad: "kg", precio: "", unidadPrecio: "kg" as UnidadPrecio,
    fecha: hoy, vence: "", factura: "", notas: "", sumar: true, guardarPrecio: true,
  });
  const [precioTocado, setPrecioTocado] = useState(false);
  const [intento, setIntento] = useState(false);
  const [guardada, setGuardada] = useState<Guardada | null>(null);

  const proveedorId = Number(f.proveedor) || 0;
  const productoCat = cat.data?.productos.find((p) => p.nombre.toLowerCase() === f.producto.trim().toLowerCase());
  const precios = useQuery({
    queryKey: ["precios-producto", productoCat?.id],
    queryFn: () => api.preciosDeProducto(productoCat!.id),
    enabled: productoCat !== undefined,
  });
  const sugerido = proveedorId ? precios.data?.precios.find((p) => p.proveedor_id === proveedorId) : undefined;
  const sugPrecio = sugerido?.precio;
  const sugUnidad = sugerido?.unidad_precio;
  useEffect(() => {
    if (sugPrecio !== undefined && sugUnidad !== undefined && !precioTocado) {
      setF((x) => ({ ...x, precio: String(sugPrecio).replace(".", ","), unidadPrecio: sugUnidad }));
    }
  }, [sugPrecio, sugUnidad, precioTocado]);

  const cantidad = aNumero(f.cantidad);
  const precio = aNumero(f.precio);
  const total = totalCompra(cantidad, f.unidad, precio, f.unidadPrecio);
  const noConvierte = Number.isFinite(cantidad) && total === null;
  const faltan: string[] = [];
  if (!proveedorId) faltan.push("Elige el proveedor.");
  if (f.producto.trim() === "") faltan.push("Escribe el producto.");
  if (!(cantidad > 0)) faltan.push("La cantidad debe ser un número mayor que cero.");
  if (noConvierte) faltan.push(`Esa unidad no se puede pasar a ${NOMBRE_PRECIO[f.unidadPrecio]}. Cambia la unidad de la cantidad o la del precio.`);
  if (!(precio > 0)) faltan.push("El precio debe ser un número mayor que cero.");
  if (f.fecha === "") faltan.push("Pon la fecha de la compra.");
  else if (f.fecha > hoy) faltan.push("La fecha de la compra no puede ser en el futuro.");

  const m = useMutation({
    mutationFn: () => api.crearCompra({
      proveedor_id: proveedorId, producto: f.producto.trim(), cantidad, unidad: f.unidad, precio, unidad_precio: f.unidadPrecio,
      fecha: f.fecha, vence: f.vence || undefined, factura: f.factura.trim() || undefined, notas: f.notas.trim() || undefined,
      crear_lote: f.sumar, actualizar_precio: f.guardarPrecio,
    }),
    onSuccess: async (r) => {
      setGuardada({ total: r.total, lote: r.lote, productoCreado: r.producto_creado });
      await refrescar();
    },
  });

  const set = (k: "producto" | "cantidad" | "fecha" | "vence" | "factura" | "notas") =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setF({ ...f, [k]: e.target.value });

  if (guardada) {
    return (
      <DialogoEdicion titulo="Compra guardada" onCerrar={onCerrar}>
        <div className="space-y-4" role="status">
          <p className="flex items-start gap-2"><CheckCircle2 className="mt-0.5 shrink-0 text-ok" size={18} aria-hidden />
            <span>Quedó anotada. Total de la compra: <strong className="tabular-nums">{dinero(guardada.total)}</strong>.</span></p>
          {guardada.lote && <p className="text-sm text-muted">Se sumó al inventario como lote {guardada.lote}.</p>}
          {guardada.productoCreado && <p className="text-sm text-muted">El producto era nuevo y se agregó a tu catálogo.</p>}
          <div className="flex justify-end"><Button type="button" variante="primario" onClick={onCerrar}>Listo</Button></div>
        </div>
      </DialogoEdicion>
    );
  }

  return (
    <DialogoEdicion titulo="Registrar compra" onCerrar={onCerrar}>
      <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); setIntento(true); if (faltan.length === 0 && !m.isPending) m.mutate(); }}>
        <div className="grid gap-4 sm:grid-cols-2">
          <Campo id="rc-prov" etiqueta="Proveedor">
            <select id="rc-prov" className={campo} value={f.proveedor} onChange={(e) => { setPrecioTocado(false); setF({ ...f, proveedor: e.target.value }); }}>
              <option value="">Elige uno…</option>
              {provs.data?.proveedores.map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}
            </select>
          </Campo>
          <Campo id="rc-prod" etiqueta="Producto">
            <input id="rc-prod" list="rc-lista" autoComplete="off" className={campo} value={f.producto}
              onChange={(e) => { setPrecioTocado(false); set("producto")(e); }} />
            <datalist id="rc-lista">{cat.data?.productos.map((p) => <option key={p.id} value={p.nombre} />)}</datalist>
          </Campo>
        </div>
        {provs.error != null && <ErrorCaja error={provs.error} onReintentar={() => void provs.refetch()} />}
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="grid grid-cols-2 gap-2">
            <Campo id="rc-cant" etiqueta="Cantidad">
              <input id="rc-cant" inputMode="decimal" className={campo} value={f.cantidad} onChange={set("cantidad")} />
            </Campo>
            <Campo id="rc-uni" etiqueta="Unidad">
              <select id="rc-uni" className={campo} value={f.unidad} onChange={(e) => setF({ ...f, unidad: e.target.value })}>
                {UNIDADES_CANTIDAD.map((u) => <option key={u.id} value={u.id}>{u.nombre}</option>)}
              </select>
            </Campo>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <Campo id="rc-precio" etiqueta="Precio ($)">
              <input id="rc-precio" inputMode="decimal" className={campo} value={f.precio}
                onChange={(e) => { setPrecioTocado(true); setF({ ...f, precio: e.target.value }); }} />
            </Campo>
            <Campo id="rc-up" etiqueta="Se vende por">
              <select id="rc-up" className={campo} value={f.unidadPrecio}
                onChange={(e) => { setPrecioTocado(true); setF({ ...f, unidadPrecio: e.target.value as UnidadPrecio }); }}>
                {UNIDADES_PRECIO.map((u) => <option key={u.id} value={u.id}>{u.nombre}</option>)}
              </select>
            </Campo>
          </div>
        </div>
        {sugerido && (
          <p className="text-sm text-muted">Último precio de este proveedor: {precioConUnidad(sugerido.precio, sugerido.unidad_precio)}. Cámbialo si hoy te cobraron otro.</p>
        )}
        <p aria-live="polite" className="rounded-xl border border-line p-3 text-sm">
          {total !== null && precio > 0
            ? <>Total calculado: <strong className="text-base tabular-nums">{dinero(total)}</strong>. El sistema confirma el total al guardar.</>
            : <span className="text-muted">Escribe cantidad y precio para ver el total.</span>}
        </p>
        <div className="grid gap-4 sm:grid-cols-2">
          <Campo id="rc-fecha" etiqueta="Fecha de la compra">
            <input id="rc-fecha" type="date" max={hoy} className={campo} value={f.fecha} onChange={set("fecha")} />
          </Campo>
          <Campo id="rc-vence" etiqueta="Vence (opcional)">
            <input id="rc-vence" type="date" className={campo} value={f.vence} onChange={set("vence")} />
          </Campo>
        </div>
        <Campo id="rc-factura" etiqueta="Número de factura (opcional)">
          <input id="rc-factura" className={campo} value={f.factura} onChange={set("factura")} />
        </Campo>
        <Campo id="rc-notas" etiqueta="Notas (opcional)">
          <textarea id="rc-notas" rows={2} className={campo} value={f.notas} onChange={set("notas")} />
        </Campo>
        <div className="space-y-2 text-sm">
          <label className="flex items-center gap-2"><input type="checkbox" checked={f.sumar} onChange={(e) => setF({ ...f, sumar: e.target.checked })} /> Sumar al inventario</label>
          <label className="flex items-center gap-2"><input type="checkbox" checked={f.guardarPrecio} onChange={(e) => setF({ ...f, guardarPrecio: e.target.checked })} /> Guardar como precio de hoy de este proveedor</label>
        </div>
        {intento && <Avisos mensajes={faltan} />}
        {noConvierte && !intento && <p role="alert" className="text-sm text-bad">Esa unidad no se puede pasar a {NOMBRE_PRECIO[f.unidadPrecio]}.</p>}
        {m.error != null && <ErrorCaja error={m.error} />}
        <div className="flex justify-end gap-2">
          <Button type="button" onClick={onCerrar}>Cancelar</Button>
          <Button type="submit" variante="primario" disabled={m.isPending || noConvierte}>{m.isPending ? "Guardando…" : "Guardar compra"}</Button>
        </div>
      </form>
    </DialogoEdicion>
  );
}
