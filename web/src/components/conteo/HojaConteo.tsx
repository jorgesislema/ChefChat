import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Check, Lock, Plus, Printer, Search, Trash2 } from "lucide-react";
import { api, type ConteoDetalle, type LineaConteo } from "../../lib/api";
import {
  avancePct, cuerpoContar, diferencia, filtrarLineas, leerCantidad, nivelDiferencia, textoCantidad, textoDiferencia, type ChipConteo,
} from "../../lib/conteo";
import { dinero, fechaEnFrase, fechaLarga } from "../../lib/format";
import { Badge, Button, Card, Cargando, ErrorCaja, Tabla, Td, Th, Vacio, cx } from "../ui/ui";
import { Dato } from "../analisis/Graficos";
import { ConfirmarQuitar, campo, useEstable } from "../edicion/comun";
import { AgregarAlConteoDialogo, CerrarConteoDialogo, type ResultadoCierre } from "./Dialogos";
import { HojaImpresa } from "./HojaImpresa";
import { useRefrescarConteo } from "./refrescar";

type Estado = "quieto" | "guardando" | "guardado" | "error";
const CHIPS: { id: ChipConteo; nombre: string }[] = [{ id: "todos", nombre: "Todos" }, { id: "sin_contar", nombre: "Sin contar" }, { id: "con_diferencia", nombre: "Con diferencia" }];
const TONO = { bad: "text-bad", warn: "text-warn", ok: "text-ok" } as const;

function Fila({ l, texto, editable, alCambiar, alIgual }: {
  l: LineaConteo; texto: string; editable: boolean; alCambiar: (t: string) => void; alIgual: () => void;
}) {
  const n = leerCantidad(texto);
  const invalido = n !== null && Number.isNaN(n);
  const dif = invalido ? null : diferencia(l.cantidad_sistema, n);
  const nivel = nivelDiferencia(dif);
  const valor = dif !== null && l.precio !== null ? Math.round(dif * l.precio * 100) / 100 : null;
  return (
    <tr>
      <Td className="font-medium">{l.producto}</Td>
      <Td className="text-muted">{l.categoria ?? "—"}</Td>
      <Td className="whitespace-nowrap text-right tabular-nums">{textoCantidad(l.cantidad_sistema)} {l.unidad}</Td>
      <Td>
        {editable ? (
          <input data-conteo inputMode="decimal" autoComplete="off" value={texto} placeholder="—" aria-label={`Cantidad contada de ${l.producto}`}
            aria-invalid={invalido || undefined} onChange={(e) => alCambiar(e.target.value)}
            onFocus={(e) => e.currentTarget.select()}
            className={cx(campo, "w-28 text-right tabular-nums", invalido && "border-bad")} />
        ) : <span className="tabular-nums">{texto === "" ? "Sin contar" : texto}</span>}
        {invalido && <span role="alert" className="mt-1 block text-xs text-bad">Escribe solo un número, por ejemplo 2,5.</span>}
      </Td>
      <Td>{l.unidad}</Td>
      <Td className="whitespace-nowrap">
        {nivel && dif !== null ? <span className={cx("font-medium", TONO[nivel.nivel])}>{nivel.texto} {dif !== 0 && textoDiferencia(dif)}</span> : <span className="text-muted">—</span>}
      </Td>
      <Td className={cx("whitespace-nowrap text-right tabular-nums", nivel && TONO[nivel.nivel])}>{valor === null ? "—" : dinero(valor)}</Td>
      {editable && (
        <Td><Button aria-label={`Igual al sistema: ${l.producto}`} onClick={alIgual} className="whitespace-nowrap px-3 py-1.5"><Check size={14} aria-hidden /> Igual al sistema</Button></Td>
      )}
    </tr>
  );
}

function Hoja({ d, alVolver }: { d: ConteoDetalle; alVolver: () => void }) {
  const refrescar = useRefrescarConteo();
  const cerrado = d.estado === "cerrado";
  const [escrito, setEscrito] = useState<Record<number, string>>({});
  const [estado, setEstado] = useState<Estado>("quieto");
  const [errorGuardar, setErrorGuardar] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [cat, setCat] = useState("");
  const [chip, setChip] = useState<ChipConteo>("todos");
  const [dlg, setDlg] = useState<"agregar" | "cerrar" | "borrar" | null>(null);
  const [resultado, setResultado] = useState<ResultadoCierre | null>(null);
  const tabla = useRef<HTMLDivElement>(null);
  const enVuelo = useRef(false);
  const fallo = useRef<Record<number, string> | null>(null);

  const { cambios, invalidos } = useMemo(() => cuerpoContar(d.lineas, escrito), [d.lineas, escrito]);
  const cats = useMemo(() => [...new Set(d.lineas.map((l) => l.categoria).filter(Boolean))].sort((a, b) => String(a).localeCompare(String(b), "es")) as string[], [d.lineas]);
  const filas = useMemo(() => filtrarLineas(d.lineas, { q, categoria: cat, chip }), [d.lineas, q, cat, chip]);
  const difValor = d.lineas.reduce((s, l) => s + (l.valor_diferencia ?? 0), 0);

  /** Guarda lo cambiado. Si falla, lo escrito se queda en pantalla. Devuelve si quedó todo guardado. */
  const guardar = useEstable(async (): Promise<boolean> => {
    if (enVuelo.current) return false;
    if (cambios.length === 0) return invalidos === 0;
    const enviado = escrito;
    const ids = new Set(cambios.map((c) => c.producto_id));
    enVuelo.current = true;
    setEstado("guardando");
    setErrorGuardar(null);
    try {
      await api.contar(d.id, cambios);
      await refrescar();
      // quita solo lo enviado que no se siguió editando
      setEscrito((prev) => Object.fromEntries(Object.entries(prev).filter(([k, t]) => !(ids.has(Number(k)) && t === enviado[Number(k)]))));
      fallo.current = null;
      setEstado("guardado");
      return invalidos === 0;
    } catch (e) {
      fallo.current = enviado;
      setErrorGuardar(e instanceof Error ? e.message : "No pude guardar. Lo que escribiste sigue aquí.");
      setEstado("error");
      return false;
    } finally {
      enVuelo.current = false;
    }
  });

  // guardado automático 2 s después de dejar de escribir (no reintenta solo si falló: espera otro cambio)
  useEffect(() => {
    if (cerrado || cambios.length === 0 || estado === "guardando" || fallo.current === escrito) return;
    const t = setTimeout(() => void guardar(), 2000);
    return () => clearTimeout(t);
  }, [escrito, cambios.length, estado, cerrado, guardar]);

  useEffect(() => {
    if (cambios.length === 0) return;
    const f = (e: BeforeUnloadEvent) => { e.preventDefault(); };
    window.addEventListener("beforeunload", f);
    return () => window.removeEventListener("beforeunload", f);
  }, [cambios.length]);

  const texto = (l: LineaConteo) => escrito[l.producto_id] ?? textoCantidad(l.cantidad_contada);
  const poner = (l: LineaConteo, t: string) => setEscrito((e) => ({ ...e, [l.producto_id]: t }));

  const enter = (e: React.KeyboardEvent) => {
    const t = e.target as HTMLElement;
    if (e.key !== "Enter" || !t.hasAttribute("data-conteo")) return;
    e.preventDefault();
    const campos = [...(tabla.current?.querySelectorAll<HTMLInputElement>("input[data-conteo]") ?? [])];
    campos[campos.indexOf(t as HTMLInputElement) + 1]?.focus();
  };

  const conGuardado = async (accion: () => void) => { if (await guardar()) accion(); };
  const imprimir = () => void conGuardado(() => setTimeout(() => window.print(), 150));

  const contadas = d.n_contadas;
  const pct = avancePct(contadas, d.n_lineas);

  return (
    <>
      <div className="no-print space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <Button onClick={() => void conGuardado(alVolver)} className="mb-2 px-3 py-1.5"><ArrowLeft size={14} aria-hidden /> Todos los conteos</Button>
            <h2 className="text-xl font-semibold">Conteo del {fechaEnFrase(d.fecha)}</h2>
            <p className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted">
              <Badge nivel={cerrado ? "ok" : "warn"}>{cerrado ? "Cerrado" : "Abierto"}</Badge>
              {d.es_demo ? "Datos de demostración" : null}
              {cerrado && d.cerrado_por ? `Cerrado por ${d.cerrado_por}` : null}
              {d.notas ? `· ${d.notas}` : null}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button onClick={imprimir}><Printer size={16} aria-hidden /> Imprimir hoja</Button>
            {!cerrado && <Button onClick={() => setDlg("agregar")}><Plus size={16} aria-hidden /> Agregar algo que no está en la hoja</Button>}
            {!cerrado && <Button variante="peligro" onClick={() => setDlg("borrar")}><Trash2 size={16} aria-hidden /> Borrar conteo</Button>}
            {!cerrado && <Button variante="primario" onClick={() => void conGuardado(() => setDlg("cerrar"))} disabled={estado === "guardando"}><Lock size={16} aria-hidden /> Cerrar conteo</Button>}
          </div>
        </div>

        {resultado && (
          <Card role="status" className="border-ok/40">
            <p className="font-semibold">Conteo cerrado.</p>
            <p className="mt-1 text-sm">
              Diferencia: <span className={cx("font-medium", resultado.diferencia < 0 ? "text-bad" : resultado.diferencia > 0 ? "text-warn" : "text-ok")}>{dinero(resultado.diferencia)}</span>
              {" "}(sistema {dinero(resultado.valor_sistema)}, contado {dinero(resultado.valor_contado)}). Ajustes al inventario: {resultado.ajustes}.
            </p>
          </Card>
        )}

        <div>
          <div className="mb-1 flex justify-between text-sm"><span>{contadas} de {d.n_lineas} contados</span><span className="tabular-nums">{pct} %</span></div>
          <div role="progressbar" aria-label="Avance del conteo" aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct} className="h-3 w-full overflow-hidden rounded-full bg-line">
            <div className="h-3 rounded-full bg-brand" style={{ width: `${pct}%` }} />
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Dato etiqueta="Valor según el sistema" valor={dinero(d.valor_sistema_actual)} />
          <Dato etiqueta="Valor contado hasta ahora" valor={dinero(d.valor_contado_actual)} />
          <Dato etiqueta="Diferencia en lo contado" valor={dinero(difValor)} tono={difValor < 0 ? "text-bad" : difValor > 0 ? "text-warn" : undefined} nota="Solo de lo que ya contaste" />
          <Dato etiqueta="Productos con diferencia grande" valor={String(d.n_alertas)} tono={d.n_alertas > 0 ? "text-bad" : undefined} />
        </div>

        {d.mensajes.length > 0 && (
          <Card>
            <h3 className="mb-2 font-semibold">Lo importante</h3>
            <ul className="list-disc space-y-1 pl-5 text-sm">{d.mensajes.map((m) => <li key={m}>{m}</li>)}</ul>
          </Card>
        )}

        <div className="flex flex-wrap items-center gap-3">
          <div className="relative min-w-60 flex-1">
            <Search size={16} className="absolute left-3 top-3 text-muted" aria-hidden />
            <label className="sr-only" htmlFor="conteo-buscar">Buscar producto</label>
            <input id="conteo-buscar" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Buscar producto…" autoComplete="off"
              className="w-full rounded-xl border border-line bg-surface py-2 pl-9 pr-3 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand" />
          </div>
          <label className="sr-only" htmlFor="conteo-cat">Categoría</label>
          <select id="conteo-cat" value={cat} onChange={(e) => setCat(e.target.value)} className="rounded-xl border border-line bg-surface px-3 py-2">
            <option value="">Todas las categorías</option>
            {cats.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          <div role="group" aria-label="Qué productos ver" className="inline-flex gap-1 rounded-xl border border-line bg-surface p-1">
            {CHIPS.map((c) => (
              <button key={c.id} type="button" aria-pressed={chip === c.id} onClick={() => setChip(c.id)}
                className={cx("rounded-lg px-3 py-1 text-sm font-medium transition", chip === c.id ? "bg-brand text-black" : "text-muted hover:text-ink")}>{c.nombre}</button>
            ))}
          </div>
        </div>

        {!cerrado && (
          <div className="sticky top-0 z-10 flex flex-wrap items-center gap-3 rounded-xl border border-line bg-surface px-4 py-2 text-sm" aria-live="polite">
            {cambios.length > 0 && <Button variante="primario" className="px-3 py-1.5" disabled={estado === "guardando"} onClick={() => { fallo.current = null; void guardar(); }}>
              Guardar ({cambios.length} {cambios.length === 1 ? "cambio" : "cambios"})</Button>}
            {estado === "guardando" && <span className="text-muted">Guardando…</span>}
            {estado === "guardado" && cambios.length === 0 && <span className="text-ok">Guardado</span>}
            {estado === "error" && <span role="alert" className="text-bad">No se pudo guardar: {errorGuardar} Lo que escribiste sigue aquí.</span>}
            {invalidos > 0 && <span className="text-bad">{invalidos} {invalidos === 1 ? "número" : "números"} sin entender: revísalos, no se guardarán.</span>}
            {estado === "quieto" && cambios.length === 0 && invalidos === 0 && <span className="text-muted">Escribe lo que hay y se guarda solo. Enter pasa al siguiente.</span>}
          </div>
        )}

        {d.lineas.length === 0 ? <Vacio titulo="La hoja no tiene productos" texto="Agrega lo que encuentres con «Agregar algo que no está en la hoja»." /> :
          filas.length === 0 ? <Vacio titulo="No encontré productos" texto="Prueba con otro nombre o cambia los filtros." /> : (
            <div ref={tabla} onKeyDown={enter}>
              <Tabla>
                <thead>
                  <tr>
                    <Th>Producto</Th><Th>Categoría</Th><Th className="text-right">El sistema dice</Th><Th className="text-right">Hay</Th><Th>Unidad</Th>
                    <Th>Diferencia</Th><Th className="text-right">Valor</Th>{!cerrado && <Th><span className="sr-only">Acciones</span></Th>}
                  </tr>
                </thead>
                <tbody>
                  {filas.map((l) => (
                    <Fila key={l.id} l={l} texto={texto(l)} editable={!cerrado} alCambiar={(t) => poner(l, t)} alIgual={() => poner(l, textoCantidad(l.cantidad_sistema))} />
                  ))}
                </tbody>
              </Tabla>
            </div>
          )}
      </div>

      <HojaImpresa d={d} />
      {dlg === "agregar" && <AgregarAlConteoDialogo id={d.id} onCerrar={() => setDlg(null)} />}
      {dlg === "cerrar" && <CerrarConteoDialogo d={d} onCerrar={() => setDlg(null)} alCerrado={setResultado} />}
      {dlg === "borrar" && (
        <ConfirmarQuitar titulo="Borrar conteo" confirmar="Sí, borrar el conteo" alCerrar={() => setDlg(null)}
          texto={`Se borra la hoja del ${fechaLarga(d.fecha)} con todo lo que ya contaste. El inventario no cambia.`}
          deshacer="No se puede deshacer. Para contar otra vez hay que empezar un conteo nuevo."
          alConfirmar={async () => { await api.anularConteo(d.id); await refrescar(); alVolver(); }} />
      )}
    </>
  );
}

export function HojaConteo({ id, alVolver }: { id: number; alVolver: () => void }) {
  const { data, error, refetch } = useQuery({ queryKey: ["conteo", id], queryFn: () => api.conteo(id) });
  if (error && !data) return <ErrorCaja error={error} onReintentar={() => refetch()} />;
  if (!data) return <Cargando filas={6} />;
  return <Hoja d={data} alVolver={alVolver} />;
}
