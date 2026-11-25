import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, type PrecioProveedor, type ProductoCat, type TipoProducto, type UnidadPrecio } from "../../lib/api";
import { aNumero, cuerpoEditaProducto, validarProducto, type FormProducto } from "../../lib/edicion";
import { cambioPrecio, precioConUnidad } from "../../lib/precios";
import { Button, Cargando, ErrorCaja, Vacio, cx } from "../ui/ui";
import { Avisos, Campo, ConfirmarQuitar, DialogoEdicion, campo, useRefrescar } from "./comun";
import { CambiarPrecioDialogo } from "./ProveedorDialogos";

export function EditarProductoDialogo({ producto, categorias, onCerrar }: { producto: ProductoCat; categorias: string[]; onCerrar: () => void }) {
  const refrescar = useRefrescar();
  const [f, setF] = useState<FormProducto>({
    nombre: producto.nombre, categoria: producto.categoria ?? "", tipo: producto.tipo,
    vidaUtil: producto.vida_util_dias === null ? "" : String(producto.vida_util_dias),
  });
  const [peso, setPeso] = useState(producto.kg_por_unidad === null ? "" : String(producto.kg_por_unidad).replace(".", ","));
  const [intento, setIntento] = useState(false);
  const pesoNum = peso.trim() === "" ? null : aNumero(peso);
  const pesoMal = pesoNum !== null && !(Number.isFinite(pesoNum) && pesoNum > 0);
  const faltan = [...validarProducto(f), ...(pesoMal ? ["El peso de 1 unidad debe ser un número mayor que cero, o déjalo vacío."] : [])];
  const m = useMutation({
    mutationFn: async () => {
      await api.editarProducto(producto.id, cuerpoEditaProducto(f));
      if (pesoNum !== producto.kg_por_unidad) await api.pesoProducto(producto.id, pesoNum);
    },
    onSuccess: async () => { await refrescar(); onCerrar(); },
  });
  return (
    <DialogoEdicion titulo={`Editar ${producto.nombre}`} onCerrar={onCerrar}>
      <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); setIntento(true); if (faltan.length === 0 && !m.isPending) m.mutate(); }}>
        <Campo id="ed-nombre" etiqueta="Nombre del producto">
          <input id="ed-nombre" className={campo} value={f.nombre} onChange={(e) => setF({ ...f, nombre: e.target.value })} />
        </Campo>
        <div className="grid gap-4 sm:grid-cols-2">
          <Campo id="ed-categoria" etiqueta="Categoría">
            <input id="ed-categoria" list="ed-categorias" autoComplete="off" className={campo} value={f.categoria} onChange={(e) => setF({ ...f, categoria: e.target.value })} />
            <datalist id="ed-categorias">{categorias.map((c) => <option key={c} value={c} />)}</datalist>
          </Campo>
          <Campo id="ed-tipo" etiqueta="Tipo">
            <select id="ed-tipo" className={campo} value={f.tipo} onChange={(e) => setF({ ...f, tipo: e.target.value as TipoProducto })}>
              <option value="alimento">Alimento</option><option value="limpieza">Limpieza</option>
            </select>
          </Campo>
        </div>
        <Campo id="ed-vida" etiqueta="Vida útil (días)" ayuda="Cuántos días dura desde que entra, si el lote no trae fecha de vencimiento.">
          <input id="ed-vida" inputMode="numeric" aria-describedby="ed-vida-ayuda" className={cx(campo, "sm:max-w-40")} value={f.vidaUtil} onChange={(e) => setF({ ...f, vidaUtil: e.target.value })} />
        </Campo>
        <Campo id="ed-peso" etiqueta="Peso de 1 unidad o 1 litro (kg)" ayuda="Ej.: huevo 0,06; aceite 0,92 por litro. Sin esto, lo que se anota en unidades no suma en el balance.">
          <input id="ed-peso" inputMode="decimal" aria-describedby="ed-peso-ayuda" className={cx(campo, "sm:max-w-40")} value={peso} onChange={(e) => setPeso(e.target.value)} />
        </Campo>
        {intento && <Avisos mensajes={faltan} />}
        {m.error != null && <ErrorCaja error={m.error} />}
        <div className="flex justify-end gap-2">
          <Button type="button" onClick={onCerrar}>Cancelar</Button>
          <Button type="submit" variante="primario" disabled={m.isPending}>{m.isPending ? "Guardando…" : "Guardar cambios"}</Button>
        </div>
      </form>
    </DialogoEdicion>
  );
}

type Sub = { tipo: "cambiar" | "quitar"; p: PrecioProveedor } | null;

function AgregarProveedor({ producto, usados }: { producto: ProductoCat; usados: number[] }) {
  const refrescar = useRefrescar();
  const provs = useQuery({ queryKey: ["proveedores"], queryFn: api.proveedores });
  const [prov, setProv] = useState("");
  const [valor, setValor] = useState("");
  const [unidad, setUnidad] = useState<UnidadPrecio>("kg");
  const [intento, setIntento] = useState(false);
  const libres = (provs.data?.proveedores ?? []).filter((p) => !usados.includes(p.id));
  const n = aNumero(valor);
  const faltan = [...(prov === "" ? ["Elige el proveedor."] : []), ...(Number.isFinite(n) && n > 0 ? [] : ["El precio debe ser un número mayor que cero."])];
  const m = useMutation({
    mutationFn: () => api.guardarPrecio(Number(prov), { producto: producto.nombre, precio: n, unidad_precio: unidad }),
    onSuccess: async () => { await refrescar(); setProv(""); setValor(""); setIntento(false); },
  });
  return (
    <form className="space-y-3 rounded-xl border border-line p-4" onSubmit={(e) => { e.preventDefault(); setIntento(true); if (faltan.length === 0 && !m.isPending) m.mutate(); }}>
      <h3 className="font-semibold">Agregar proveedor</h3>
      {provs.error ? <ErrorCaja error={provs.error} onReintentar={() => provs.refetch()} /> : libres.length === 0 && provs.data ? (
        <p className="text-sm text-muted">Todos tus proveedores ya venden este producto. Crea uno nuevo en la pantalla de Proveedores.</p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-3">
          <Campo id="ap-prov" etiqueta="Proveedor">
            <select id="ap-prov" className={campo} value={prov} onChange={(e) => setProv(e.target.value)} disabled={!provs.data}>
              <option value="">Elige uno…</option>
              {libres.map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}
            </select>
          </Campo>
          <Campo id="ap-precio" etiqueta="Precio ($)"><input id="ap-precio" inputMode="decimal" className={campo} value={valor} onChange={(e) => setValor(e.target.value)} placeholder="0,00" /></Campo>
          <Campo id="ap-unidad" etiqueta="Se vende por">
            <select id="ap-unidad" className={campo} value={unidad} onChange={(e) => setUnidad(e.target.value as UnidadPrecio)}>
              <option value="kg">kg</option><option value="l">litro</option><option value="unidad">unidad</option>
            </select>
          </Campo>
        </div>
      )}
      {intento && <Avisos mensajes={faltan} />}
      {m.error != null && <ErrorCaja error={m.error} />}
      <Button type="submit" variante="primario" disabled={m.isPending || libres.length === 0}>{m.isPending ? "Guardando…" : "Agregar proveedor"}</Button>
    </form>
  );
}

/** Proveedores que venden un producto, del más barato al más caro. Desde aquí se cambia o quita un precio, o se suma otro proveedor. */
export function PreciosProductoDialogo({ producto, onCerrar }: { producto: ProductoCat; onCerrar: () => void }) {
  const refrescar = useRefrescar();
  const q = useQuery({ queryKey: ["precios-producto", producto.id], queryFn: () => api.preciosDeProducto(producto.id) });
  const [sub, setSub] = useState<Sub>(null);
  const precios = useMemo(() => [...(q.data?.precios ?? [])].sort((a, b) => a.precio - b.precio), [q.data]);
  if (sub?.tipo === "cambiar") {
    const { p } = sub;
    return <CambiarPrecioDialogo proveedorId={p.proveedor_id} proveedor={p.proveedor} producto={producto.nombre} precio={p.precio} unidad={p.unidad_precio} onCerrar={() => setSub(null)} />;
  }
  if (sub?.tipo === "quitar") {
    const { p } = sub;
    return (
      <ConfirmarQuitar titulo="Quitar de este proveedor" confirmar="Sí, quitar" alCerrar={() => setSub(null)}
        texto={`${p.proveedor} ya no vende ${producto.nombre}. El historial de precios se conserva.`}
        alConfirmar={async () => { await api.quitarProductoDeProveedor(p.proveedor_id, producto.id); await refrescar(); }} />
    );
  }
  return (
    <DialogoEdicion titulo={`Precios de ${producto.nombre}`} onCerrar={onCerrar}>
      <div className="space-y-4">
        {q.error ? <ErrorCaja error={q.error} onReintentar={() => q.refetch()} /> : !q.data ? <Cargando filas={3} /> : precios.length === 0 ? (
          <Vacio titulo="Nadie te vende este producto todavía" texto="Agrega un proveedor con su precio para poder comparar." />
        ) : (
          <ul className="divide-y divide-line rounded-xl border border-line" aria-label="Proveedores de este producto">
            {precios.map((p, i) => {
              const c = cambioPrecio(p.cambio_pct);
              return (
                <li key={p.proveedor_id} className="flex flex-wrap items-center gap-x-4 gap-y-2 p-3">
                  <div className="min-w-40 flex-1">
                    <p className="font-medium">{p.proveedor}{i === 0 && precios.length > 1 && <span className="ml-2 text-xs font-normal text-ok">Más barato</span>}</p>
                    <p className="text-sm tabular-nums text-muted">
                      {precioConUnidad(p.precio, p.unidad_precio)} · {p.fecha}
                      {c && <span className={cx("ml-2", c.nivel === "bad" && "text-bad", c.nivel === "ok" && "text-ok")}>{c.flecha} {c.texto}</span>}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button aria-label={`Cambiar precio de ${producto.nombre} en ${p.proveedor}`} onClick={() => setSub({ tipo: "cambiar", p })}>Cambiar precio</Button>
                    <Button variante="peligro" aria-label={`Quitar a ${p.proveedor} de ${producto.nombre}`} onClick={() => setSub({ tipo: "quitar", p })}>Quitar</Button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
        {q.data && <AgregarProveedor producto={producto} usados={precios.map((p) => p.proveedor_id)} />}
        <div className="flex justify-end"><Button onClick={onCerrar}>Cerrar</Button></div>
      </div>
    </DialogoEdicion>
  );
}
