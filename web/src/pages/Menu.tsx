import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Printer, RefreshCw } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { api, type ComidaSugerida, type DiaSugerido, type MenuSugerencia } from "../lib/api";
import { Badge, Button, Card, Cargando, ErrorCaja, Pagina, Pestanas, Skeleton, Vacio, cx } from "../components/ui/ui";
import { Foquito } from "../components/Foquito";
import { diasRestantes, etiquetaDias, fechaLarga } from "../lib/format";
import { NOMBRE_COMIDA, PLAZOS, leerTope, pestanaMenu, textoStock, type PestanaMenu } from "../lib/menu";
import { precio } from "../lib/precios";
import { AccionesSobrante } from "../components/analisis/AccionesSobrante";

const COMIDAS = ["desayuno", "almuerzo", "merienda", "cena"];
const PEST: { id: PestanaMenu; nombre: string }[] = [
  { id: "cocinar", nombre: "Qué cocinar" }, { id: "armar", nombre: "Armar menú" },
  { id: "costos", nombre: "Costo por persona" }, { id: "sobrantes", nombre: "Sobrantes" },
];
const dinero = (n: number | null) => (n === null ? "—" : precio(n));
const fechaCorta = (iso: string) => fechaLarga(iso).replace(/ de \d{4}$/, "").toLowerCase();

function Chips({ opciones, elegidos, onCambia, etiqueta }: { opciones: string[]; elegidos: string[]; onCambia: (v: string[]) => void; etiqueta: string }) {
  return (
    <div role="group" aria-label={etiqueta} className="flex flex-wrap gap-2">
      {opciones.map((a) => {
        const on = elegidos.includes(a);
        return (
          <button key={a} type="button" aria-pressed={on}
            onClick={() => onCambia(on ? elegidos.filter((x) => x !== a) : [...elegidos, a])}
            className={cx("rounded-full border px-3 py-1 text-sm transition", on ? "border-brand bg-brand text-black font-medium" : "border-line text-muted hover:text-ink")}>
            {a}
          </button>
        );
      })}
    </div>
  );
}

function Evitar({ valor, onCambia }: { valor: string[]; onCambia: (v: string[]) => void }) {
  const q = useQuery({ queryKey: ["menu-alergenos"], queryFn: api.menuAlergenos });
  if (q.error) return <p className="text-sm text-muted">No pude cargar la lista de alérgenos.</p>;
  if (!q.data) return <Skeleton className="h-8 w-full max-w-md" />;
  return <Chips opciones={q.data.alergenos} elegidos={valor} onCambia={onCambia} etiqueta="Alérgenos a evitar" />;
}

// ---- Qué cocinar ----
function Cocinar() {
  const [dias, setDias] = useState(1);
  const [sin, setSin] = useState<string[]>([]);
  const q = useQuery({ queryKey: ["menu-cocinar", dias, sin], queryFn: () => api.menuCocinar(dias, sin), placeholderData: (p) => p });
  return (
    <div className="space-y-5">
      <div className="no-print flex flex-wrap items-center gap-3">
        <div role="group" aria-label="Plazo" className="inline-flex gap-1 rounded-xl border border-line bg-surface p-1">
          {PLAZOS.map((p) => (
            <button key={p.id} type="button" aria-pressed={dias === p.id} onClick={() => setDias(p.id)}
              className={cx("rounded-lg px-3 py-1 text-sm font-medium transition", dias === p.id ? "bg-brand text-black" : "text-muted hover:text-ink")}>{p.nombre}</button>
          ))}
        </div>
      </div>
      <div><p className="mb-2 text-sm text-muted">Evitar alérgenos</p><Evitar valor={sin} onCambia={setSin} /></div>
      {q.error ? <ErrorCaja error={q.error} onReintentar={() => q.refetch()} /> : !q.data ? <Cargando filas={4} /> : (
        <>
          {q.data.aviso && <p role="note" className="rounded-xl border border-warn/40 bg-warn/10 p-3 text-sm text-warn">{q.data.aviso}</p>}
          <Card>
            <h2 className="mb-3 text-lg font-semibold">Lo que vence</h2>
            {q.data.por_vencer.length === 0 ? (
              <Vacio titulo="Nada vence en ese plazo. No hace falta cocinar con urgencia." />
            ) : (
              <ul className="divide-y divide-line">
                {q.data.por_vencer.map((p) => (
                  <li key={p.producto_id} className="flex flex-wrap items-center justify-between gap-2 py-2.5">
                    <span className="flex items-center gap-2 font-medium">{p.producto}<Foquito dias={p.dias} /></span>
                    <span className="flex items-center gap-3 text-sm text-muted">
                      <span>{textoStock(p.stock)}</span>
                      <Badge nivel={p.dias <= 1 ? "bad" : "warn"}>{etiquetaDias(p.dias)}</Badge>
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
          {q.data.por_vencer.length > 0 && (
            <div>
              <h2 className="mb-3 text-lg font-semibold">Recetas que puedes cocinar</h2>
              {q.data.recetas.length === 0 ? <Vacio titulo="No encontré recetas que usen estos productos" texto="Prueba quitando algún alérgeno de la lista." /> : (
                <ul className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                  {q.data.recetas.map((r) => (
                    <li key={r.id_receta} className="rounded-2xl border border-line bg-surface p-4">
                      <p className="font-semibold">{r.nombre}</p>
                      {r.categoria && <p className="text-sm text-muted">{r.categoria}</p>}
                      <p className="mt-2 text-sm">Costo por plato: <strong>{dinero(r.costo_plato)}</strong></p>
                      <p className="text-sm">Alcanza para hasta <strong>{r.porciones_posibles}</strong> {r.porciones_posibles === 1 ? "plato" : "platos"}</p>
                      {r.usa.length > 0 && (
                        <ul className="mt-2 space-y-1 text-sm text-muted" aria-label="Productos que vencen y usa">
                          {r.usa.map((u) => (
                            <li key={u.producto} className="flex items-center gap-1.5"><Foquito dias={u.dias} />{u.producto} · {etiquetaDias(u.dias).toLowerCase()}</li>
                          ))}
                        </ul>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ---- Armar menú ----
function ComidaTarjeta({ c }: { c: ComidaSugerida }) {
  return (
    <div className="rounded-xl border border-line p-3">
      <h4 className="font-semibold">{NOMBRE_COMIDA[c.servicio] ?? c.servicio}</h4>
      {c.platos.length === 0 ? <p className="mt-1 text-sm text-muted">No encontré platos para esta comida.</p> : (
        <ul className="mt-1 divide-y divide-line/60">
          {c.platos.map((p) => (
            <li key={p.id_receta} className="flex items-start justify-between gap-3 py-1.5 text-sm">
              <span>
                <span className="inline-flex items-center gap-1.5">{p.nombre}{p.usa_por_vencer.length > 0 && (
                  <span title={`Usa lo que vence: ${p.usa_por_vencer.join(", ")}`} aria-label={`Usa lo que vence: ${p.usa_por_vencer.join(", ")}`} role="img" className="text-warn">💡</span>)}</span>
                {p.usa_por_vencer.length > 0 && <span className="block text-xs text-muted">Usa: {p.usa_por_vencer.join(", ")}</span>}
              </span>
              <span className="whitespace-nowrap tabular-nums">{dinero(p.costo_plato)}</span>
            </li>
          ))}
        </ul>
      )}
      <p className="mt-1 text-right text-sm font-medium tabular-nums">= {dinero(c.costo_persona)} por persona</p>
      {!c.cumple_tope && (
        <p role="note" className="mt-2 rounded-lg border border-warn/40 bg-warn/10 p-2 text-sm text-warn">
          {c.nota ?? "Esta comida pasa del costo máximo que pusiste."}
        </p>
      )}
    </div>
  );
}

function DiaTarjeta({ d }: { d: DiaSugerido }) {
  return (
    <Card className="space-y-3 break-inside-avoid">
      <h3 className="text-lg font-semibold">{fechaLarga(d.fecha)}</h3>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">{d.comidas.map((c) => <ComidaTarjeta key={c.servicio} c={c} />)}</div>
      <p className="text-right font-semibold tabular-nums">Total del día: {dinero(d.costo_persona)} por persona</p>
    </Card>
  );
}

function Resultado({ data }: { data: MenuSugerencia }) {
  return (
    <div className="print-area space-y-4">
      {data.aviso && <p role="note" className="rounded-xl border border-warn/40 bg-warn/10 p-3 text-sm text-warn">{data.aviso}</p>}
      {!data.cumple_tope && data.tope_dia !== null && (
        <p role="note" className="rounded-xl border border-warn/40 bg-warn/10 p-3 text-sm text-warn">
          Este menú pasa del costo máximo de {precio(data.tope_dia)} por persona al día. Mira el detalle en cada comida.
        </p>
      )}
      {data.dias.map((d) => <DiaTarjeta key={d.fecha} d={d} />)}
      {data.costo_promedio_dia !== null && data.dias.length > 1 && (
        <p className="text-sm text-muted">Costo promedio por día: <strong className="text-ink">{precio(data.costo_promedio_dia)}</strong> por persona.</p>
      )}
    </div>
  );
}

function Armar() {
  const [comidas, setComidas] = useState<string[]>(["desayuno", "almuerzo", "merienda"]);
  const [tope, setTope] = useState("");
  const [sin, setSin] = useState<string[]>([]);
  const [dias, setDias] = useState(1);
  const [porVencer, setPorVencer] = useState(true);
  const [pedido, setPedido] = useState<{ semilla: number; params: Parameters<typeof api.menuSugerencia>[0] } | null>(null);
  const topeNum = leerTope(tope);
  const topeMal = tope.trim() !== "" && topeNum === null;
  const armar = (semilla: number) =>
    setPedido({ semilla, params: { comidas: COMIDAS.filter((c) => comidas.includes(c)), tope: topeNum, sin, dias, por_vencer: porVencer, semilla } });
  const q = useQuery({ queryKey: ["menu-sugerencia", pedido], queryFn: () => api.menuSugerencia(pedido!.params), enabled: pedido !== null });
  const puede = comidas.length > 0 && !topeMal;
  return (
    <div className="space-y-5">
      <form className="no-print space-y-4 rounded-2xl border border-line bg-surface p-5" onSubmit={(e) => { e.preventDefault(); if (puede) armar(0); }}>
        <fieldset>
          <legend className="mb-2 text-sm text-muted">Comidas del día</legend>
          <div className="flex flex-wrap gap-4">
            {COMIDAS.map((c) => (
              <label key={c} className="inline-flex items-center gap-2">
                <input type="checkbox" checked={comidas.includes(c)} className="h-4 w-4 accent-brand"
                  onChange={(e) => setComidas(e.target.checked ? [...comidas, c] : comidas.filter((x) => x !== c))} />
                {NOMBRE_COMIDA[c]}
              </label>
            ))}
          </div>
          {comidas.length === 0 && <p className="mt-1 text-xs text-bad">Elige al menos una comida.</p>}
        </fieldset>
        <div className="flex flex-wrap gap-6">
          <div>
            <label htmlFor="mn-tope" className="mb-1 block text-sm text-muted">Costo máximo por persona al día (opcional)</label>
            <div className="flex items-center gap-2">
              <span aria-hidden>$</span>
              <input id="mn-tope" inputMode="decimal" value={tope} onChange={(e) => setTope(e.target.value)} placeholder="Ej. 12" aria-invalid={topeMal}
                className="w-28 rounded-xl border border-line bg-bg px-3 py-2" />
            </div>
            {topeMal && <p className="mt-1 text-xs text-bad">Escribe un número mayor que cero, por ejemplo 12 o 12,50.</p>}
          </div>
          <div>
            <p className="mb-1 text-sm text-muted">Días</p>
            <div role="group" aria-label="Días" className="inline-flex gap-1 rounded-xl border border-line bg-bg p-1">
              {[1, 3, 7].map((n) => (
                <button key={n} type="button" aria-pressed={dias === n} onClick={() => setDias(n)}
                  className={cx("rounded-lg px-3 py-1 text-sm font-medium", dias === n ? "bg-brand text-black" : "text-muted hover:text-ink")}>{n}</button>
              ))}
            </div>
          </div>
        </div>
        <div><p className="mb-2 text-sm text-muted">Evitar</p><Evitar valor={sin} onCambia={setSin} /></div>
        <label className="inline-flex items-center gap-2">
          <input type="checkbox" role="switch" checked={porVencer} onChange={(e) => setPorVencer(e.target.checked)} className="h-4 w-4 accent-brand" />
          Usar primero lo que vence pronto
        </label>
        <div className="flex flex-wrap gap-2">
          <Button type="submit" variante="primario" disabled={!puede || q.isFetching}>{q.isFetching ? "Armando…" : "Armar menú"}</Button>
          {pedido && <Button type="button" disabled={!puede || q.isFetching} onClick={() => armar(pedido.semilla + 1)}><RefreshCw size={16} aria-hidden /> Otra propuesta</Button>}
          {q.data && <Button type="button" onClick={() => window.print()}><Printer size={16} aria-hidden /> Imprimir menú</Button>}
        </div>
      </form>
      {!pedido ? <Vacio titulo="Aquí aparecerá tu menú" texto="Elige las comidas y toca «Armar menú»." /> :
        q.error ? <ErrorCaja error={q.error} onReintentar={() => q.refetch()} /> :
        !q.data ? <Cargando filas={3} /> : <Resultado data={q.data} />}
    </div>
  );
}

// ---- Costo por persona ----
function Costos() {
  const q = useQuery({ queryKey: ["menu-costos"], queryFn: api.menuCostos });
  if (q.error) return <ErrorCaja error={q.error} onReintentar={() => q.refetch()} />;
  if (!q.data) return <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" role="status" aria-label="Cargando">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-44" />)}</div>;
  return (
    <div className="space-y-4">
      <p className="text-muted">Es la suma del costo por plato de cada parte de la comida.</p>
      <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {COMIDAS.map((c) => {
          const x = q.data.por_comida[c as keyof typeof q.data.por_comida];
          return (
            <li key={c} className="rounded-2xl border border-line bg-surface p-5">
              <h2 className="font-medium text-muted">{NOMBRE_COMIDA[c]}</h2>
              {x ? (
                <>
                  <p className="mt-2 text-3xl font-bold tabular-nums">{precio(x.tipico)}</p>
                  <p className="text-sm text-muted">Desde {precio(x.minimo)} hasta {precio(x.maximo)}</p>
                  {x.platos.length > 0 && <p className="mt-3 text-sm"><span className="text-muted">Se compone de: </span>{x.platos.join(", ")}</p>}
                </>
              ) : <p className="mt-2 text-sm text-muted">Todavía no hay platos para esta comida.</p>}
            </li>
          );
        })}
      </ul>
      {q.data.nota && <p className="text-xs text-muted">{q.data.nota}</p>}
    </div>
  );
}

// ---- Sobrantes ----
function Sobrantes() {
  const q = useQuery({ queryKey: ["menu-sobrantes"], queryFn: api.menuSobrantes });
  if (q.error) return <ErrorCaja error={q.error} onReintentar={() => q.refetch()} />;
  if (!q.data) return <Cargando filas={3} />;
  const l = q.data.sobrantes;
  if (l.length === 0) return <Vacio titulo="No hay sobrantes registrados" texto="Cuando sobre comida preparada, aparecerá aquí con ideas para aprovecharla." />;
  return (
    <ul className="grid gap-4 md:grid-cols-2">
      {l.map((s) => {
        const dias = diasRestantes(s.usar_hasta);
        return (
          <li key={s.id} className="rounded-2xl border border-line bg-surface p-5">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <p className="font-semibold">{s.producto}</p>
              <Badge nivel={s.vigente ? (dias <= 0 ? "warn" : "ok") : "bad"}>{s.vigente ? "Se puede usar" : "No usar"}</Badge>
            </div>
            <p className="mt-1 text-sm text-muted">{String(s.cantidad).replace(".", ",")} {s.unidad} · Usar hasta el {fechaCorta(s.usar_hasta)}</p>
            {!s.vigente ? (
              <p role="alert" className="mt-3 font-medium text-bad">{s.mensaje ?? "Pasó el plazo sanitario. No se debe reutilizar."}</p>
            ) : s.recetas.length === 0 ? (
              <p className="mt-3 text-sm text-muted">No encontré recetas para aprovecharlo.</p>
            ) : (
              <div className="mt-3">
                <p className="text-sm text-muted">Puedes usarlo en:</p>
                <ul className="mt-1 space-y-1 text-sm">{s.recetas.map((r) => (
                  <li key={r.id_receta} className="flex justify-between gap-3"><span>{r.nombre}</span><span className="tabular-nums text-muted">{dinero(r.costo_plato)} por plato</span></li>))}</ul>
              </div>
            )}
            <AccionesSobrante s={s} />
          </li>
        );
      })}
    </ul>
  );
}

export default function Menu() {
  const [sp, setSp] = useSearchParams();
  const pest = pestanaMenu(sp.get("pestana"));
  return (
    <Pagina titulo="Menú" subtitulo="Qué cocinar, cuánto cuesta cada comida y cómo aprovechar lo que sobra.">
      <div className="no-print"><Pestanas valor={pest} onCambia={(v) => setSp({ pestana: v }, { replace: true })} items={PEST} /></div>
      {pest === "cocinar" ? <Cocinar /> : pest === "armar" ? <Armar /> : pest === "costos" ? <Costos /> : <Sobrantes />}
    </Pagina>
  );
}
