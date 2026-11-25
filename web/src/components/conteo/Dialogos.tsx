import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, type ConteoDetalle, type UnidadPrecio } from "../../lib/api";
import { leerCantidad, resumenCierre } from "../../lib/conteo";
import { dinero } from "../../lib/format";
import { Button, ErrorCaja, cx } from "../ui/ui";
import { Avisos, Campo, DialogoEdicion, campo } from "../edicion/comun";
import { useRefrescarConteo } from "./refrescar";

export function AgregarAlConteoDialogo({ id, onCerrar }: { id: number; onCerrar: () => void }) {
  const refrescar = useRefrescarConteo();
  const cat = useQuery({ queryKey: ["catalogo"], queryFn: api.catalogo });
  const [producto, setProducto] = useState("");
  const [cantidad, setCantidad] = useState("");
  const [unidad, setUnidad] = useState<UnidadPrecio>("kg");
  const [intento, setIntento] = useState(false);
  const n = leerCantidad(cantidad);
  const faltan = [
    ...(producto.trim() === "" ? ["Escribe el nombre del producto."] : []),
    ...(n === null || Number.isNaN(n) ? ["Escribe la cantidad como número, por ejemplo 2,5."] : []),
  ];
  const m = useMutation({
    mutationFn: () => api.agregarAlConteo(id, { producto: producto.trim(), cantidad: n as number, unidad }),
    onSuccess: async () => { await refrescar(); onCerrar(); },
  });
  return (
    <DialogoEdicion titulo="Agregar algo que no está en la hoja" onCerrar={onCerrar}>
      <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); setIntento(true); if (faltan.length === 0 && !m.isPending) m.mutate(); }}>
        <p className="text-sm text-muted">Úsalo para algo que encontraste y el sistema no tenía en el almacén. Elige un producto que ya exista en tu lista.</p>
        <Campo id="ac-producto" etiqueta="Producto">
          <input id="ac-producto" list="ac-catalogo" autoComplete="off" className={campo} value={producto} onChange={(e) => setProducto(e.target.value)} />
          <datalist id="ac-catalogo">{(cat.data?.productos ?? []).map((p) => <option key={p.id} value={p.nombre} />)}</datalist>
        </Campo>
        <div className="grid gap-4 sm:grid-cols-2">
          <Campo id="ac-cantidad" etiqueta="Cantidad que encontraste">
            <input id="ac-cantidad" inputMode="decimal" className={campo} value={cantidad} onChange={(e) => setCantidad(e.target.value)} placeholder="0" autoComplete="off" />
          </Campo>
          <Campo id="ac-unidad" etiqueta="Unidad">
            <select id="ac-unidad" className={campo} value={unidad} onChange={(e) => setUnidad(e.target.value as UnidadPrecio)}>
              <option value="kg">kg</option><option value="l">litro (l)</option><option value="unidad">unidad</option>
            </select>
          </Campo>
        </div>
        {intento && <Avisos mensajes={faltan} />}
        {m.error != null && <ErrorCaja error={m.error} />}
        <div className="flex justify-end gap-2">
          <Button type="button" onClick={onCerrar}>Cancelar</Button>
          <Button type="submit" variante="primario" disabled={m.isPending}>{m.isPending ? "Agregando…" : "Agregar a la hoja"}</Button>
        </div>
      </form>
    </DialogoEdicion>
  );
}

export type ResultadoCierre = { valor_sistema: number; valor_contado: number; diferencia: number; ajustes: number };

export function CerrarConteoDialogo({ d, onCerrar, alCerrado }: { d: ConteoDetalle; onCerrar: () => void; alCerrado: (r: ResultadoCierre) => void }) {
  const refrescar = useRefrescarConteo();
  const [nombre, setNombre] = useState("");
  const [ajustar, setAjustar] = useState(true);
  const [sinContarIgual, setSinContarIgual] = useState(false);
  const [intento, setIntento] = useState(false);
  const r = resumenCierre(d.lineas, d.valor_sistema_actual, d.valor_contado_actual, sinContarIgual);
  const faltan = [
    ...(nombre.trim() === "" ? ["Escribe quién cierra el conteo."] : []),
    ...(r.sinContar > 0 && !sinContarIgual ? [`Faltan ${r.sinContar} productos por contar. Marca la casilla de abajo o vuelve a la hoja y cuéntalos.`] : []),
  ];
  const m = useMutation({
    mutationFn: () => api.cerrarConteo(d.id, { cerrado_por: nombre.trim(), ajustar_inventario: ajustar, sin_contar_igual: sinContarIgual }),
    onSuccess: async (res) => { await refrescar(); alCerrado(res); onCerrar(); },
  });
  return (
    <DialogoEdicion titulo="Cerrar conteo" onCerrar={onCerrar}>
      <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); setIntento(true); if (faltan.length === 0 && !m.isPending) m.mutate(); }}>
        <Campo id="cc-nombre" etiqueta="¿Quién cierra el conteo?">
          <input id="cc-nombre" className={campo} value={nombre} onChange={(e) => setNombre(e.target.value)} autoComplete="name" />
        </Campo>
        <label className="flex items-start gap-2 text-sm">
          <input type="checkbox" className="mt-1" checked={ajustar} onChange={(e) => setAjustar(e.target.checked)} />
          <span>
            <span className="font-medium">Ajustar el inventario a lo contado</span>
            <span className="block text-muted">Lo que falta se descuenta de lo que vence antes. Lo que sobra entra como un lote de ajuste.</span>
          </span>
        </label>
        {r.sinContar > 0 && (
          <label className="flex items-start gap-2 text-sm">
            <input type="checkbox" className="mt-1" checked={sinContarIgual} onChange={(e) => setSinContarIgual(e.target.checked)} />
            <span className="font-medium">Para los {r.sinContar} que no conté, usar lo que dice el sistema</span>
          </label>
        )}
        <dl className="grid gap-2 rounded-xl border border-line p-3 text-sm sm:grid-cols-3">
          <div><dt className="text-muted">Valor según el sistema</dt><dd className="font-semibold tabular-nums">{dinero(r.sistema)}</dd></div>
          <div><dt className="text-muted">Valor contado</dt><dd className="font-semibold tabular-nums">{dinero(r.contado)}</dd></div>
          <div><dt className="text-muted">Diferencia</dt><dd className={cx("font-semibold tabular-nums", r.diferencia < 0 && "text-bad", r.diferencia > 0 && "text-warn")}>{dinero(r.diferencia)}</dd></div>
        </dl>
        <p className="text-sm font-medium text-warn">Después de cerrar ya no se puede cambiar.</p>
        {intento && <Avisos mensajes={faltan} />}
        {m.error != null && <ErrorCaja error={m.error} />}
        <div className="flex justify-end gap-2">
          <Button type="button" onClick={onCerrar}>Volver a la hoja</Button>
          <Button type="submit" variante="primario" disabled={m.isPending}>{m.isPending ? "Cerrando…" : "Cerrar conteo"}</Button>
        </div>
      </form>
    </DialogoEdicion>
  );
}
