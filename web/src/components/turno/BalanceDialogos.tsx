import { useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type TipoSalida, type Turno } from "../../lib/api";
import { aNumero } from "../../lib/edicion";
import { Button } from "../ui/ui";
import { Avisos, Campo, DialogoEdicion, campo, useRefrescar } from "../edicion/comun";

const UNIDADES = ["kg", "g", "l", "ml", "libra", "qq", "unidad"];

interface Base { fecha: string; turno: Turno; onCerrar: () => void }

function useGuardar<T>(fecha: string, turno: Turno, hacer: () => Promise<T>, alTerminar: (r: T) => void) {
  const qc = useQueryClient();
  const refrescar = useRefrescar();
  const [errores, setErrores] = useState<string[]>([]);
  const m = useMutation({
    mutationFn: hacer,
    onSuccess: async (r) => {
      await Promise.all([qc.invalidateQueries({ queryKey: ["balance", fecha, turno] }), refrescar()]);
      alTerminar(r);
    },
    onError: (e) => setErrores([e instanceof Error ? e.message : "No pude guardar. Intenta de nuevo."]),
  });
  return { m, errores, setErrores };
}

function Pie({ pendiente, onCerrar, texto }: { pendiente: boolean; onCerrar: () => void; texto: string }) {
  return (
    <div className="flex justify-end gap-2">
      <Button type="button" onClick={onCerrar}>Cancelar</Button>
      <Button type="submit" variante="primario" disabled={pendiente}>{pendiente ? "Guardando…" : texto}</Button>
    </div>
  );
}

function Productos() {
  const q = useQuery({ queryKey: ["catalogo"], queryFn: api.catalogo });
  return <datalist id="bal-productos">{(q.data?.productos ?? []).map((p) => <option key={p.id} value={p.nombre} />)}</datalist>;
}

function Unidades({ id, valor, alCambiar }: { id: string; valor: string; alCambiar: (v: string) => void }) {
  return (
    <select id={id} className={campo} value={valor} onChange={(e) => alCambiar(e.target.value)}>
      {UNIDADES.map((u) => <option key={u} value={u}>{u}</option>)}
    </select>
  );
}

function Formulario({ alEnviar, children }: { alEnviar: () => void; children: ReactNode }) {
  return <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); alEnviar(); }}>{children}</form>;
}

/** Entrega de bodega o devolución a bodega. */
export function DialogoMovimiento({ tipo, fecha, turno, onCerrar }: Base & { tipo: "entrega" | "devolucion" }) {
  const [producto, setProducto] = useState("");
  const [cantidad, setCantidad] = useState("");
  const [unidad, setUnidad] = useState("kg");
  const [entrego, setEntrego] = useState("");
  const [recibio, setRecibio] = useState("");
  const [descontar, setDescontar] = useState(true);
  const [aviso, setAviso] = useState<string | null>(null);
  const n = aNumero(cantidad);
  const { m, errores, setErrores } = useGuardar(fecha, turno, () => api.anotarMovimiento({
    fecha, turno, tipo, producto: producto.trim(), cantidad: n, unidad,
    ...(entrego.trim() ? { entrego: entrego.trim() } : {}), ...(recibio.trim() ? { recibio: recibio.trim() } : {}),
    descontar_inventario: descontar,
  }), (r) => { if (r.aviso) setAviso(r.aviso); else onCerrar(); });

  const enviar = () => {
    const faltan = [...(producto.trim() ? [] : ["Escribe el producto."]), ...(Number.isFinite(n) && n > 0 ? [] : ["La cantidad debe ser un número mayor que cero."])];
    setErrores(faltan);
    if (faltan.length === 0 && !m.isPending) m.mutate();
  };
  const titulo = tipo === "entrega" ? "Entrega de bodega" : "Devolución a bodega";

  if (aviso) {
    return (
      <DialogoEdicion titulo={titulo} onCerrar={onCerrar}>
        <div className="space-y-4">
          <p role="status" className="rounded-xl border border-warn/40 bg-warn/10 p-3 text-sm text-warn">{aviso}</p>
          <p className="text-sm">Quedó anotado.</p>
          <div className="flex justify-end"><Button variante="primario" onClick={onCerrar}>Cerrar</Button></div>
        </div>
      </DialogoEdicion>
    );
  }
  return (
    <DialogoEdicion titulo={titulo} onCerrar={onCerrar}>
      <Formulario alEnviar={enviar}>
        <Campo id="bm-producto" etiqueta="Producto">
          <input id="bm-producto" list="bal-productos" autoComplete="off" className={campo} value={producto} onChange={(e) => setProducto(e.target.value)} />
          <Productos />
        </Campo>
        <div className="grid gap-4 sm:grid-cols-2">
          <Campo id="bm-cantidad" etiqueta="Cantidad">
            <input id="bm-cantidad" inputMode="decimal" className={campo} value={cantidad} onChange={(e) => setCantidad(e.target.value)} />
          </Campo>
          <Campo id="bm-unidad" etiqueta="Unidad"><Unidades id="bm-unidad" valor={unidad} alCambiar={setUnidad} /></Campo>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Campo id="bm-entrego" etiqueta="Quién entregó"><input id="bm-entrego" className={campo} value={entrego} onChange={(e) => setEntrego(e.target.value)} /></Campo>
          <Campo id="bm-recibio" etiqueta="Quién recibió"><input id="bm-recibio" className={campo} value={recibio} onChange={(e) => setRecibio(e.target.value)} /></Campo>
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={descontar} onChange={(e) => setDescontar(e.target.checked)} /> Descontar del inventario
        </label>
        <Avisos mensajes={errores} />
        <Pie pendiente={m.isPending} onCerrar={onCerrar} texto="Guardar" />
      </Formulario>
    </DialogoEdicion>
  );
}

/** Merma pesada del turno. */
export function DialogoMerma({ fecha, turno, onCerrar }: Base) {
  const [producto, setProducto] = useState("");
  const [cantidad, setCantidad] = useState("");
  const [unidad, setUnidad] = useState("kg");
  const [motivo, setMotivo] = useState("");
  const n = aNumero(cantidad);
  const { m, errores, setErrores } = useGuardar(fecha, turno, () => api.anotarMermaTurno({
    fecha, turno, producto: producto.trim(), cantidad: n, unidad, motivo: motivo.trim(),
  }), () => onCerrar());
  const enviar = () => {
    const faltan = [
      ...(producto.trim() ? [] : ["Escribe el producto."]),
      ...(Number.isFinite(n) && n > 0 ? [] : ["La cantidad debe ser un número mayor que cero."]),
      ...(motivo.trim() ? [] : ["Escribe el motivo."]),
    ];
    setErrores(faltan);
    if (faltan.length === 0 && !m.isPending) m.mutate();
  };
  return (
    <DialogoEdicion titulo="Merma pesada" onCerrar={onCerrar}>
      <Formulario alEnviar={enviar}>
        <Campo id="bw-producto" etiqueta="Producto">
          <input id="bw-producto" list="bal-productos" autoComplete="off" className={campo} value={producto} onChange={(e) => setProducto(e.target.value)} />
          <Productos />
        </Campo>
        <div className="grid gap-4 sm:grid-cols-2">
          <Campo id="bw-cantidad" etiqueta="Cantidad">
            <input id="bw-cantidad" inputMode="decimal" className={campo} value={cantidad} onChange={(e) => setCantidad(e.target.value)} />
          </Campo>
          <Campo id="bw-unidad" etiqueta="Unidad"><Unidades id="bw-unidad" valor={unidad} alCambiar={setUnidad} /></Campo>
        </div>
        <Campo id="bw-motivo" etiqueta="Motivo" ayuda="Por ejemplo: se quemó, se cayó, se echó a perder.">
          <input id="bw-motivo" aria-describedby="bw-motivo-ayuda" className={campo} value={motivo} onChange={(e) => setMotivo(e.target.value)} />
        </Campo>
        <Avisos mensajes={errores} />
        <Pie pendiente={m.isPending} onCerrar={onCerrar} texto="Guardar" />
      </Formulario>
    </DialogoEdicion>
  );
}

/** Comida del personal o residuo de limpieza (en kilos). */
export function DialogoSalida({ tipo, fecha, turno, onCerrar }: Base & { tipo: Extract<TipoSalida, "comida_personal" | "residuo_limpieza"> }) {
  const [kgTxt, setKgTxt] = useState("");
  const [nota, setNota] = useState("");
  const [persona, setPersona] = useState("");
  const n = aNumero(kgTxt);
  const { m, errores, setErrores } = useGuardar(fecha, turno, () => api.anotarSalida({
    fecha, turno, tipo, kg: n, ...(nota.trim() ? { nota: nota.trim() } : {}), ...(persona.trim() ? { persona: persona.trim() } : {}),
  }), () => onCerrar());
  const enviar = () => {
    const faltan = Number.isFinite(n) && n > 0 ? [] : ["Los kilos deben ser un número mayor que cero."];
    setErrores(faltan);
    if (faltan.length === 0 && !m.isPending) m.mutate();
  };
  return (
    <DialogoEdicion titulo={tipo === "comida_personal" ? "Comida del personal" : "Residuo de limpieza"} onCerrar={onCerrar}>
      <Formulario alEnviar={enviar}>
        <Campo id="bs-kg" etiqueta="Kilos">
          <input id="bs-kg" inputMode="decimal" className={`${campo} sm:max-w-40`} value={kgTxt} onChange={(e) => setKgTxt(e.target.value)} />
        </Campo>
        <Campo id="bs-nota" etiqueta="Nota"><input id="bs-nota" className={campo} value={nota} onChange={(e) => setNota(e.target.value)} /></Campo>
        <Campo id="bs-persona" etiqueta="Persona"><input id="bs-persona" className={campo} value={persona} onChange={(e) => setPersona(e.target.value)} /></Campo>
        <Avisos mensajes={errores} />
        <Pie pendiente={m.isPending} onCerrar={onCerrar} texto="Guardar" />
      </Formulario>
    </DialogoEdicion>
  );
}
