import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api, type Proveedor, type UnidadPrecio } from "../../lib/api";
import { aNumero, textoDiferenciaPrecio } from "../../lib/edicion";
import { precioConUnidad } from "../../lib/precios";
import { Button, ErrorCaja } from "../ui/ui";
import { Avisos, Campo, DialogoEdicion, campo, useRefrescar } from "./comun";

export function EditarProveedorDialogo({ proveedor, onCerrar }: { proveedor: Proveedor; onCerrar: () => void }) {
  const refrescar = useRefrescar();
  const [f, setF] = useState({
    nombre: proveedor.nombre, contacto: proveedor.contacto ?? "", telefono: proveedor.telefono ?? "",
    dias_entrega: proveedor.dias_entrega ?? "", notas: proveedor.notas ?? "",
  });
  const [intento, setIntento] = useState(false);
  const m = useMutation({
    mutationFn: () => api.editarProveedor(proveedor.id, {
      nombre: f.nombre.trim(), contacto: f.contacto.trim(), telefono: f.telefono.trim(),
      dias_entrega: f.dias_entrega.trim(), notas: f.notas.trim(),
    }),
    onSuccess: async () => { await refrescar(); onCerrar(); },
  });
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setF({ ...f, [k]: e.target.value });
  const faltan = f.nombre.trim() === "" ? ["Escribe el nombre del proveedor."] : [];
  return (
    <DialogoEdicion titulo="Editar datos del proveedor" onCerrar={onCerrar}>
      <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); setIntento(true); if (faltan.length === 0 && !m.isPending) m.mutate(); }}>
        <Campo id="ep-nombre" etiqueta="Nombre del proveedor"><input id="ep-nombre" className={campo} value={f.nombre} onChange={set("nombre")} /></Campo>
        <div className="grid gap-4 sm:grid-cols-2">
          <Campo id="ep-contacto" etiqueta="Persona de contacto"><input id="ep-contacto" className={campo} value={f.contacto} onChange={set("contacto")} /></Campo>
          <Campo id="ep-tel" etiqueta="Teléfono"><input id="ep-tel" type="tel" className={campo} value={f.telefono} onChange={set("telefono")} /></Campo>
        </div>
        <Campo id="ep-dias" etiqueta="Días de entrega"><input id="ep-dias" placeholder="Por ejemplo: lunes y jueves" className={campo} value={f.dias_entrega} onChange={set("dias_entrega")} /></Campo>
        <Campo id="ep-notas" etiqueta="Notas"><textarea id="ep-notas" rows={2} className={campo} value={f.notas} onChange={set("notas")} /></Campo>
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

const NOMBRE_UNIDAD: Record<UnidadPrecio, string> = { kg: "kg", l: "litro", unidad: "unidad" };

interface CambiarPrecioProps {
  proveedorId: number; proveedor: string; producto: string; precio: number; unidad: UnidadPrecio; onCerrar: () => void;
}

/** Cambia el precio de un producto de un proveedor. Muestra el precio anterior y la diferencia antes de guardar. */
export function CambiarPrecioDialogo({ proveedorId, proveedor, producto, precio, unidad, onCerrar }: CambiarPrecioProps) {
  const refrescar = useRefrescar();
  const [valor, setValor] = useState(String(precio).replace(".", ","));
  const [u, setU] = useState<UnidadPrecio>(unidad);
  const [intento, setIntento] = useState(false);
  const nuevo = aNumero(valor);
  const valido = Number.isFinite(nuevo) && nuevo > 0;
  const m = useMutation({
    mutationFn: () => api.guardarPrecio(proveedorId, { producto, precio: nuevo, unidad_precio: u }),
    onSuccess: async () => { await refrescar(); onCerrar(); },
  });
  const diferencia = valido && u === unidad ? textoDiferenciaPrecio(precio, nuevo) : "";
  return (
    <DialogoEdicion titulo={`Cambiar precio de ${producto}`} onCerrar={onCerrar}>
      <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); setIntento(true); if (valido && !m.isPending) m.mutate(); }}>
        <p className="text-sm text-muted">{proveedor} te lo vende a {precioConUnidad(precio, unidad)}.</p>
        <div className="grid gap-4 sm:grid-cols-2">
          <Campo id="cp-precio" etiqueta="Precio nuevo ($)">
            <input id="cp-precio" inputMode="decimal" className={campo} value={valor} onChange={(e) => setValor(e.target.value)} />
          </Campo>
          <Campo id="cp-unidad" etiqueta="Se vende por">
            <select id="cp-unidad" className={campo} value={u} onChange={(e) => setU(e.target.value as UnidadPrecio)}>
              {(Object.keys(NOMBRE_UNIDAD) as UnidadPrecio[]).map((k) => <option key={k} value={k}>{NOMBRE_UNIDAD[k]}</option>)}
            </select>
          </Campo>
        </div>
        <p aria-live="polite" className="min-h-5 text-sm">
          {diferencia && <>Antes: {precioConUnidad(precio, unidad)}. Al guardar, el precio <strong>{diferencia}</strong>.</>}
          {valido && u !== unidad && <span className="text-muted">Cambiaste la unidad, por eso no se compara con el precio anterior.</span>}
        </p>
        {intento && !valido && <Avisos mensajes={["El precio debe ser un número mayor que cero."]} />}
        {m.error != null && <ErrorCaja error={m.error} />}
        <div className="flex justify-end gap-2">
          <Button type="button" onClick={onCerrar}>Cancelar</Button>
          <Button type="submit" variante="primario" disabled={m.isPending}>{m.isPending ? "Guardando…" : "Guardar precio"}</Button>
        </div>
      </form>
    </DialogoEdicion>
  );
}
