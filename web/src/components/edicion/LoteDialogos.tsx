import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, type LoteInv } from "../../lib/api";
import { UNIDADES_LOTE, cuerpoEditaLote, cuerpoNuevoLote, hoyISO, validarLote, type FormLote } from "../../lib/edicion";
import { Button, ErrorCaja } from "../ui/ui";
import { Avisos, Campo, DialogoEdicion, campo, useRefrescar } from "./comun";

const NOMBRE_UNIDAD: Record<string, string> = { kg: "kg", g: "g", l: "litro (l)", ml: "mililitro (ml)", libra: "libra", qq: "quintal (qq)", unidad: "unidad" };

function SelectorUnidad({ id, valor, onCambia }: { id: string; valor: string; onCambia: (v: string) => void }) {
  const extra = (UNIDADES_LOTE as readonly string[]).includes(valor) ? [] : [valor]; // unidad antigua que no está en la lista
  return (
    <select id={id} className={campo} value={valor} onChange={(e) => onCambia(e.target.value)}>
      {[...UNIDADES_LOTE, ...extra].map((u) => <option key={u} value={u}>{NOMBRE_UNIDAD[u] ?? u}</option>)}
    </select>
  );
}

export function AgregarLoteDialogo({ onCerrar }: { onCerrar: () => void }) {
  const refrescar = useRefrescar();
  const cat = useQuery({ queryKey: ["catalogo"], queryFn: api.catalogo });
  const [f, setF] = useState<FormLote>({ producto: "", cantidad: "", unidad: "kg", fechaIngreso: hoyISO(), vence: "", idLote: "", categoria: "" });
  const [intento, setIntento] = useState(false);
  const productos = cat.data?.productos ?? [];
  const existe = productos.some((p) => p.nombre.toLowerCase() === f.producto.trim().toLowerCase());
  const categorias = useMemo(() => [...new Set(productos.map((p) => p.categoria).filter(Boolean))].sort() as string[], [productos]);
  const faltan = validarLote(f);
  const m = useMutation({
    mutationFn: () => api.crearLote(cuerpoNuevoLote(f, existe)),
    onSuccess: async () => { await refrescar(); onCerrar(); },
  });
  const set = (k: keyof FormLote) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value });
  return (
    <DialogoEdicion titulo="Agregar lote" onCerrar={onCerrar}>
      <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); setIntento(true); if (faltan.length === 0 && !m.isPending) m.mutate(); }}>
        <Campo id="al-producto" etiqueta="Producto">
          <input id="al-producto" list="al-catalogo" autoComplete="off" className={campo} value={f.producto} onChange={set("producto")} />
          <datalist id="al-catalogo">{productos.map((p) => <option key={p.id} value={p.nombre} />)}</datalist>
        </Campo>
        <div className="grid gap-4 sm:grid-cols-2">
          <Campo id="al-cantidad" etiqueta="Cantidad">
            <input id="al-cantidad" inputMode="decimal" className={campo} value={f.cantidad} onChange={set("cantidad")} placeholder="0" />
          </Campo>
          <Campo id="al-unidad" etiqueta="Unidad">
            <SelectorUnidad id="al-unidad" valor={f.unidad} onCambia={(unidad) => setF({ ...f, unidad })} />
          </Campo>
          <Campo id="al-ingreso" etiqueta="Fecha de ingreso">
            <input id="al-ingreso" type="date" className={campo} value={f.fechaIngreso} onChange={set("fechaIngreso")} />
          </Campo>
          <Campo id="al-vence" etiqueta="Vencimiento (opcional)" ayuda="Si lo dejas vacío se usa la vida útil del producto.">
            <input id="al-vence" type="date" aria-describedby="al-vence-ayuda" className={campo} value={f.vence} onChange={set("vence")} />
          </Campo>
          <Campo id="al-codigo" etiqueta="Código de lote (opcional)">
            <input id="al-codigo" className={campo} value={f.idLote} onChange={set("idLote")} autoComplete="off" />
          </Campo>
          {f.producto.trim() !== "" && !existe && !cat.isLoading && (
            <Campo id="al-categoria" etiqueta="Categoría (opcional)" ayuda="Ese producto aún no está en tu lista. Se agregará con este lote.">
              <input id="al-categoria" list="al-categorias" autoComplete="off" className={campo} value={f.categoria} onChange={set("categoria")} />
              <datalist id="al-categorias">{categorias.map((c) => <option key={c} value={c} />)}</datalist>
            </Campo>
          )}
        </div>
        {intento && <Avisos mensajes={faltan} />}
        {m.error != null && <ErrorCaja error={m.error} />}
        <div className="flex justify-end gap-2">
          <Button type="button" onClick={onCerrar}>Cancelar</Button>
          <Button type="submit" variante="primario" disabled={m.isPending}>{m.isPending ? "Guardando…" : "Agregar lote"}</Button>
        </div>
      </form>
    </DialogoEdicion>
  );
}

export function EditarLoteDialogo({ lote, onCerrar }: { lote: LoteInv; onCerrar: () => void }) {
  const refrescar = useRefrescar();
  const [f, setF] = useState<FormLote>({
    producto: lote.producto, cantidad: String(lote.cantidad).replace(".", ","), unidad: lote.unidad, fechaIngreso: lote.fecha_ingreso,
    vence: lote.fecha_caducidad_fija ?? "", idLote: lote.lote ?? "", categoria: "", usarVidaUtil: lote.fecha_caducidad_fija === null,
  });
  const [intento, setIntento] = useState(false);
  const faltan = validarLote(f, { editando: true });
  const m = useMutation({
    mutationFn: () => api.editarLote(lote.id, cuerpoEditaLote(f)),
    onSuccess: async () => { await refrescar(); onCerrar(); },
  });
  const set = (k: keyof FormLote) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value });
  return (
    <DialogoEdicion titulo={`Editar lote de ${lote.producto}`} onCerrar={onCerrar}>
      <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); setIntento(true); if (faltan.length === 0 && !m.isPending) m.mutate(); }}>
        <p className="text-sm text-muted">Lote {lote.lote ?? "sin código"}. Hoy vence el {lote.vence}.</p>
        <div className="grid gap-4 sm:grid-cols-2">
          <Campo id="el-cantidad" etiqueta="Cantidad">
            <input id="el-cantidad" inputMode="decimal" className={campo} value={f.cantidad} onChange={set("cantidad")} />
          </Campo>
          <Campo id="el-unidad" etiqueta="Unidad">
            <SelectorUnidad id="el-unidad" valor={f.unidad} onCambia={(unidad) => setF({ ...f, unidad })} />
          </Campo>
          <Campo id="el-ingreso" etiqueta="Fecha de ingreso">
            <input id="el-ingreso" type="date" className={campo} value={f.fechaIngreso} onChange={set("fechaIngreso")} />
          </Campo>
          <Campo id="el-vence" etiqueta="Vencimiento">
            <input id="el-vence" type="date" disabled={f.usarVidaUtil} className={`${campo} disabled:opacity-50`} value={f.vence} onChange={set("vence")} />
          </Campo>
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={!!f.usarVidaUtil} onChange={(e) => setF({ ...f, usarVidaUtil: e.target.checked })} />
          Usar la vida útil del producto
        </label>
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
