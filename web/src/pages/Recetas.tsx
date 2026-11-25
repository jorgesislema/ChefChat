import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Clock, Printer, Search } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { api, type CargaRecetas, type RecetaDetalle, type RecetaResumen } from "../lib/api";
import { BotonCargar } from "../components/BotonCargar";
import { Badge, Button, Card, Cargando, ErrorCaja, Pagina, Skeleton, Tabla, Td, Th, Vacio, cx } from "../components/ui/ui";
import { avisoDiferencia } from "../lib/menu";
import { nivelMargen, precio, textoMargen } from "../lib/precios";
import { aNumero } from "../lib/edicion";
import { Avisos, Campo, campo } from "../components/edicion/comun";

const COBERTURA_MINIMA = 0.8;

const listaAlergenos = (a: string | null) =>
  (a ?? "").split(/[,;]/).map((x) => x.trim()).filter((x) => x && !/^(ninguno|ninguna|ningún|n\/a|-)$/i.test(x));
const tiempo = (t: string | number | null) => (t === null || t === "" ? null : typeof t === "number" ? `${t} min` : /^\d+$/.test(t) ? `${t} min` : t);
const cant = (n: number | null) => (n === null ? "" : String(Math.round(n * 100) / 100).replace(".", ","));

function Alergenos({ valor }: { valor: string | null }) {
  const l = listaAlergenos(valor);
  if (l.length === 0) return <span className="text-sm text-muted">Sin alérgenos anotados</span>;
  return <ul className="flex flex-wrap gap-1.5" aria-label="Alérgenos">{l.map((a) => (
    <li key={a} className="rounded-full border border-line px-2 py-0.5 text-xs">{a}</li>))}</ul>;
}

function Tarjeta({ r, activa, onElige }: { r: RecetaResumen; activa: boolean; onElige: () => void }) {
  const t = tiempo(r.tiempo_prep);
  return (
    <li>
      <button onClick={onElige} aria-current={activa ? "true" : undefined}
        className={cx("w-full rounded-2xl border p-4 text-left transition hover:bg-line/40", activa ? "border-brand bg-brand/10" : "border-line bg-surface")}>
        <span className="flex flex-wrap items-start justify-between gap-2">
          <span className="font-semibold">{r.nombre}</span>
          {r.cobertura < COBERTURA_MINIMA && <Badge nivel="warn">Costo parcial</Badge>}
        </span>
        <span className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted">
          {r.categoria && <span>{r.categoria}</span>}
          {t && <span className="inline-flex items-center gap-1"><Clock size={13} aria-hidden />{t}</span>}
        </span>
        {listaAlergenos(r.alergenos).length > 0 && (
          <span className="mt-2 flex flex-wrap gap-1.5">{listaAlergenos(r.alergenos).map((a) => (
            <span key={a} className="rounded-full border border-line px-2 py-0.5 text-xs">{a}</span>))}</span>
        )}
        <span className="mt-2 flex flex-wrap gap-x-4 text-sm">
          <span>Costo por plato: <strong>{r.costo_plato === null ? "—" : precio(r.costo_plato)}</strong></span>
          {r.precio_venta !== null && <span>Precio de venta: <strong>{precio(r.precio_venta)}</strong></span>}
        </span>
        <span className="mt-0.5 block text-xs text-muted">{r.fuente_costo === "archivo" ? "Costo del archivo de recetas" : "Calculado con precios"}</span>
      </button>
    </li>
  );
}

function Porciones({ f }: { f: RecetaDetalle }) {
  const qc = useQueryClient();
  const [v, setV] = useState(String(f.porciones_usadas));
  useEffect(() => setV(String(f.porciones_usadas)), [f.porciones_usadas, f.id_receta]);
  const n = Number(v);
  const valido = Number.isInteger(n) && n >= 1 && n <= 500;
  const m = useMutation({
    mutationFn: () => api.guardarPorciones(f.id_receta, n),
    onSuccess: () => Promise.all(["receta", "recetas"].map((k) => qc.invalidateQueries({ queryKey: [k] }))),
  });
  return (
    <div className="no-print">
      <label htmlFor="porciones" className="mb-1 block text-sm text-muted">Porciones que rinde</label>
      <form className="flex items-center gap-2" onSubmit={(e) => { e.preventDefault(); if (valido) m.mutate(); }}>
        <input id="porciones" type="number" min={1} max={500} step={1} inputMode="numeric" value={v} onChange={(e) => setV(e.target.value)}
          aria-invalid={!valido} className="w-24 rounded-xl border border-line bg-bg px-3 py-2" />
        <Button type="submit" disabled={!valido || m.isPending || n === f.porciones_usadas && !f.porciones_supuestas}>{m.isPending ? "Guardando…" : "Guardar"}</Button>
      </form>
      {!valido && <p className="mt-1 text-xs text-bad">Escribe un número entero entre 1 y 500.</p>}
      {m.error != null && <div className="mt-2"><ErrorCaja error={m.error} /></div>}
    </div>
  );
}

function Estandar({ id }: { id: string }) {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["estandar", id], queryFn: () => api.estandar(id) });
  const [peso, setPeso] = useState("");
  const [perdida, setPerdida] = useState("");
  const [tol, setTol] = useState("");
  const [notas, setNotas] = useState("");
  const [errores, setErrores] = useState<string[]>([]);
  const [ok, setOk] = useState(false);
  const e = q.data;
  useEffect(() => {
    if (!e) return;
    setPeso(e.peso_unidad_g === null ? "" : String(e.peso_unidad_g).replace(".", ","));
    setPerdida(String(e.perdida_normal_pct).replace(".", ",")); setTol(String(e.tolerancia_pct).replace(".", ","));
    setNotas(e.notas ?? ""); setErrores([]);  // no borra «Estándar guardado»: esto corre otra vez justo después de guardar
  }, [e]);
  useEffect(() => { setOk(false); }, [id]);
  const m = useMutation({
    mutationFn: (b: { peso_unidad_g: number | null; perdida_normal_pct: number; tolerancia_pct: number; notas?: string }) => api.guardarEstandar(id, b),
    onSuccess: async () => { setOk(true); await Promise.all([qc.invalidateQueries({ queryKey: ["estandar", id] }), qc.invalidateQueries({ queryKey: ["balance"] })]); },
    onError: (x) => { setOk(false); setErrores([x instanceof Error ? x.message : "No pude guardar. Intenta de nuevo."]); },
  });
  const guardar = () => {
    const p = peso.trim() === "" ? null : aNumero(peso);
    const l = aNumero(perdida);
    const t = aNumero(tol);
    const faltan = [
      ...(p === null || (Number.isFinite(p) && p > 0) ? [] : ["El peso por unidad debe ser un número mayor que cero, o déjalo vacío."]),
      ...(Number.isFinite(l) && l >= 0 && l < 60 ? [] : ["La pérdida normal debe estar entre 0 y 60 %."]),
      ...(Number.isFinite(t) && t > 0 && t <= 30 ? [] : ["La tolerancia debe estar entre 0 y 30 % (más que cero)."]),
    ];
    setErrores(faltan); setOk(false);
    if (faltan.length === 0 && !m.isPending) m.mutate({ peso_unidad_g: p, perdida_normal_pct: l, tolerancia_pct: t, ...(notas.trim() ? { notas: notas.trim() } : {}) });
  };
  return (
    <Card className="no-print space-y-3" aria-label="Estándar de producción" role="region">
      <h3 className="text-lg font-semibold">Estándar de producción</h3>
      {q.error ? <ErrorCaja error={q.error} onReintentar={() => q.refetch()} /> : !e ? <Cargando filas={2} /> : (
        <form className="space-y-3" onSubmit={(ev) => { ev.preventDefault(); guardar(); }}>
          {e.es_defecto && <p className="text-sm text-muted">Usa el estándar por defecto (3 % y 2 %). Pesa 3 a 5 tandas en tu cocina y anótalo aquí.</p>}
          <div className="grid gap-3 sm:grid-cols-3">
            <Campo id="es-peso" etiqueta="Peso de 1 unidad (g)" ayuda="Opcional.">
              <input id="es-peso" inputMode="decimal" aria-describedby="es-peso-ayuda" className={campo} value={peso} onChange={(x) => setPeso(x.target.value)} />
            </Campo>
            <Campo id="es-perdida" etiqueta="Pérdida normal (%)">
              <input id="es-perdida" inputMode="decimal" className={campo} value={perdida} onChange={(x) => setPerdida(x.target.value)} />
            </Campo>
            <Campo id="es-tol" etiqueta="Tolerancia (%)">
              <input id="es-tol" inputMode="decimal" className={campo} value={tol} onChange={(x) => setTol(x.target.value)} />
            </Campo>
          </div>
          <Campo id="es-notas" etiqueta="Notas"><input id="es-notas" className={campo} value={notas} onChange={(x) => setNotas(x.target.value)} /></Campo>
          <Avisos mensajes={errores} />
          {ok && <p role="status" className="rounded-xl border border-ok/40 bg-ok/10 p-3 text-sm text-ok">Estándar guardado.</p>}
          <Button type="submit" variante="primario" disabled={m.isPending}>{m.isPending ? "Guardando…" : "Guardar estándar"}</Button>
        </form>
      )}
    </Card>
  );
}

function Ficha({ id }: { id: string }) {
  const q = useQuery({ queryKey: ["receta", id], queryFn: () => api.receta(id) });
  if (q.error) return <ErrorCaja error={q.error} onReintentar={() => q.refetch()} />;
  if (!q.data) return <div role="status" aria-label="Cargando" className="space-y-3"><Skeleton className="h-10 w-2/3" /><Skeleton className="h-40 w-full" /><Skeleton className="h-24 w-full" /></div>;
  const f = q.data;
  const pct = Math.round(f.cobertura * 100);
  const t = tiempo(f.tiempo_prep);
  const pasos = (f.instrucciones ?? "").split(/\r?\n|\s+(?=\d+[.)]\s)/).map((x) => x.trim()).filter(Boolean);
  return (
    <article className="print-area space-y-4">
      <Card className="space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-2xl font-bold">{f.nombre}</h2>
            <p className="mt-1 flex flex-wrap items-center gap-x-3 text-sm text-muted">
              {f.categoria && <span>{f.categoria}</span>}
              {t && <span className="inline-flex items-center gap-1"><Clock size={14} aria-hidden />Tiempo: {t}</span>}
            </p>
          </div>
          <Button className="no-print" onClick={() => window.print()}><Printer size={16} aria-hidden /> Imprimir ficha</Button>
        </div>
        <div><h3 className="mb-1 text-sm font-semibold">Alérgenos</h3><Alergenos valor={f.alergenos} /></div>
      </Card>

      <div>
        <h3 className="mb-2 text-lg font-semibold">Ingredientes</h3>
        {f.ingredientes.length === 0 ? <Vacio titulo="Esta receta no tiene ingredientes anotados" /> : (
          <Tabla>
            <thead><tr><Th>Ingrediente</Th><Th>Cantidad</Th><Th className="text-right">Costo</Th></tr></thead>
            <tbody>
              {f.ingredientes.map((i, k) => (
                <tr key={`${i.ingrediente}-${k}`}>
                  <Td className="font-medium">{i.ingrediente}</Td>
                  <Td className="whitespace-nowrap">{[cant(i.cantidad), i.unidad].filter(Boolean).join(" ") || "—"}</Td>
                  <Td className="text-right tabular-nums">
                    {i.costo !== null ? precio(i.costo) : <span className="text-muted">{i.nota || "Sin costo"}</span>}
                  </Td>
                </tr>
              ))}
            </tbody>
          </Tabla>
        )}
      </div>

      <Card className="space-y-4">
        <h3 className="text-lg font-semibold">Costos</h3>
        <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <dt className="text-sm text-muted">Costo por plato</dt>
            <dd className="text-3xl font-bold tabular-nums">{f.costo_plato === null ? "—" : precio(f.costo_plato)}</dd>
            <dd className="mt-1 text-xs text-muted">
              {f.fuente_costo === "archivo" ? "Costo del archivo de recetas" : <Badge nivel="warn">Calculado con precios</Badge>}
            </dd>
          </div>
          {f.precio_venta !== null && <div><dt className="text-sm text-muted">Precio de venta</dt><dd className="text-xl font-semibold tabular-nums">{precio(f.precio_venta)}</dd></div>}
          {f.precio_venta !== null && f.margen_pct !== null && (
            <div><dt className="text-sm text-muted">Margen</dt><dd><Badge nivel={nivelMargen(f.margen_pct)}>{textoMargen(f.margen_pct)}</Badge></dd></div>
          )}
        </dl>
        <div className="rounded-xl border border-line p-3 text-sm">
          <p className="font-medium">Con tus precios de proveedores</p>
          <p className="mt-1 text-muted">
            {f.costo_porcion === null ? "Todavía no hay precios para calcularlo." : <>
              <strong className="text-ink">{precio(f.costo_porcion)}</strong> por porción
              {f.costo_calculado !== null && <> ({precio(f.costo_calculado)} toda la receta)</>}
            </>}
          </p>
          {avisoDiferencia(f.diferencia_pct) && <p role="note" className="mt-2 text-warn">{avisoDiferencia(f.diferencia_pct)}</p>}
        </div>
        <Porciones f={f} />
        {f.porciones_supuestas && (
          <p role="note" className="rounded-xl border border-warn/40 bg-warn/10 p-3 text-sm text-warn">
            Aún no sabemos cuántas porciones rinde. Se supone 1. Cámbialo para ver el costo por porción real.
          </p>
        )}
        <div>
          <p className="text-sm">Se pudo costear el {pct} % de los ingredientes.</p>
          <div className="mt-1 h-2 overflow-hidden rounded-full bg-line" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label="Ingredientes con costo">
            <div className={cx("h-full", pct >= 100 ? "bg-ok" : "bg-warn")} style={{ width: `${pct}%` }} />
          </div>
          {pct < 100 && <p className="mt-2 text-sm font-medium text-warn">El costo está incompleto. Faltan precios de algunos ingredientes.</p>}
        </div>
      </Card>

      <Estandar id={f.id_receta} />

      <div>
        <h3 className="mb-2 text-lg font-semibold">Preparación</h3>
        {pasos.length === 0 ? <p className="text-sm text-muted">No hay pasos anotados.</p> : (
          <ol className="list-decimal space-y-2 pl-5">{pasos.map((p, i) => <li key={i}>{p.replace(/^\d+[.)]\s*/, "")}</li>)}</ol>
        )}
      </div>
    </article>
  );
}

export default function Recetas() {
  const [q, setQ] = useState("");
  const [cat, setCat] = useState("");
  const [qDif, setQDif] = useState("");
  const [sp, setSp] = useSearchParams();
  const elegida = sp.get("receta");
  const setElegida = (id: string) => setSp({ receta: id }, { replace: true });
  useEffect(() => { const t = setTimeout(() => setQDif(q.trim()), 250); return () => clearTimeout(t); }, [q]);
  const r = useQuery({ queryKey: ["recetas", qDif, cat], queryFn: () => api.recetas({ q: qDif, categoria: cat }), placeholderData: (prev) => prev });
  const lista = r.data?.recetas ?? [];
  const qc = useQueryClient();
  const cargar = (
    <BotonCargar<CargaRecetas>
      etiqueta="Cargar recetas" aceptar=".csv" ayuda="Archivo CSV con tus recetas (el mismo formato de data_source)."
      subir={api.cargarRecetas}
      alTerminar={() => { void qc.invalidateQueries({ queryKey: ["recetas"] }); void qc.invalidateQueries({ queryKey: ["receta"] }); void qc.invalidateQueries({ queryKey: ["menu"] }); }}
      resumen={(c) => (
        <div className="space-y-1">
          <p className="font-medium">{c.archivo}: {c.nuevas} recetas nuevas, {c.actualizadas} actualizadas{c.n_rechazadas ? `, ${c.n_rechazadas} rechazadas` : ""}.</p>
          {c.rechazadas.length > 0 && (
            <ul className="list-disc pl-5 text-muted">
              {c.rechazadas.map((x) => <li key={x.fila}>Fila {x.fila}: {x.motivo}</li>)}
              {c.n_rechazadas > c.rechazadas.length && <li>Y {c.n_rechazadas - c.rechazadas.length} más.</li>}
            </ul>
          )}
        </div>
      )}
    />
  );
  return (
    <Pagina titulo="Recetas" subtitulo="Cuánto cuesta cada plato y cuánto te deja de ganancia." accion={cargar}>
      <div className="no-print flex flex-wrap gap-3">
        <div className="relative min-w-60 flex-1">
          <Search size={16} className="absolute left-3 top-3 text-muted" aria-hidden />
          <label className="sr-only" htmlFor="rc-buscar">Buscar receta</label>
          <input id="rc-buscar" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Buscar receta…" className="w-full rounded-xl border border-line bg-surface py-2 pl-9 pr-3" />
        </div>
        <label className="sr-only" htmlFor="rc-cat">Categoría</label>
        <select id="rc-cat" value={cat} onChange={(e) => setCat(e.target.value)} className="rounded-xl border border-line bg-surface px-3 py-2">
          <option value="">Todas las categorías</option>
          {(r.data?.categorias ?? []).map((c) => <option key={c}>{c}</option>)}
        </select>
      </div>
      {r.error ? <ErrorCaja error={r.error} onReintentar={() => r.refetch()} /> : !r.data ? <Cargando filas={5} /> : lista.length === 0 ? (
        <Vacio titulo="No encontré recetas" texto={qDif || cat ? "Prueba con otro nombre o cambia la categoría." : "Aún no hay recetas cargadas."} />
      ) : (
        <div className="grid gap-6 xl:grid-cols-[22rem_1fr]">
          <ul className="no-print space-y-2 xl:max-h-[75vh] xl:overflow-y-auto xl:pr-1" aria-label="Lista de recetas">
            {lista.map((x) => <Tarjeta key={x.id_receta} r={x} activa={x.id_receta === elegida} onElige={() => setElegida(x.id_receta)} />)}
          </ul>
          <div className="min-w-0">
            {elegida ? <Ficha key={elegida} id={elegida} /> : (
              <Vacio titulo="Elige una receta" texto="Toca una receta de la lista para ver sus ingredientes, costos y pasos." />
            )}
          </div>
        </div>
      )}
    </Pagina>
  );
}
