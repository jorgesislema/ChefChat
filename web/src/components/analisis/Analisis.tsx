import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type AnalisisMermas, type AnalisisProduccion, type AnalisisRecuperacion, type AnalisisRentables, type PlatoRent } from "../../lib/api";
import { Badge, Button, ErrorCaja, Skeleton, Tabla, Td, Th, Vacio, cx } from "../ui/ui";
import { atajosFechas, nivelMargen, textoPct, anchoBarra } from "../../lib/analisis";
import { dinero, fechaEnFrase } from "../../lib/format";
import { colorEstado, etiquetaEstado, kg, pct } from "../../lib/balance";
import { nombreTurno } from "../../lib/turno";
import { NOMBRE_COMIDA } from "../../lib/menu";
import { CostoReal } from "./CostoReal";
import { BarrasHorizontales, ColumnasMes, Dato, Seccion } from "./Graficos";

const veces = (n: number) => `${n} ${n === 1 ? "vez" : "veces"}`;
const sinDatos = (m: string[], f: string) => m[0] ?? f;

function Mermas({ d }: { d: AnalisisMermas }) {
  return (
    <Seccion titulo="Mermas: dinero que se pierde" periodo={d.periodo} mensajes={d.mensajes}>
      {d.registros === 0 ? (
        <Vacio titulo="No hay mermas en estas fechas" texto={sinDatos(d.mensajes, "Prueba con otras fechas o toca «Todo».")} />
      ) : (
        <>
          <p className="text-3xl font-bold tabular-nums text-bad">{dinero(d.total)}
            <span className="ml-2 text-base font-normal text-muted">perdidos en {d.registros} {d.registros === 1 ? "registro" : "registros"}</span></p>
          <ColumnasMes columnas={d.por_mes.map((m) => ({ clave: m.mes, etiqueta: m.texto, valor: m.costo, dias: m.dias_con_datos }))} />
          <div className="grid gap-6 lg:grid-cols-2">
            <BarrasHorizontales titulo="Por motivo" relleno="bg-bad"
              filas={d.por_motivo.map((x) => ({ clave: x.motivo, etiqueta: x.motivo, valor: x.costo, detalle: `${dinero(x.costo)} · ${veces(x.veces)} · ${textoPct(x.pct)}` }))} />
            <BarrasHorizontales titulo="Por producto (los 10 que más cuestan)" relleno="bg-bad"
              filas={d.por_producto.slice(0, 10).map((x) => ({ clave: x.producto, etiqueta: x.producto, valor: x.costo, detalle: `${dinero(x.costo)} · ${veces(x.veces)} · ${textoPct(x.pct)}` }))} />
          </div>
        </>
      )}
    </Seccion>
  );
}

function Recuperacion({ d }: { d: AnalisisRecuperacion }) {
  const vacio = d.reutilizados + d.desperdiciados + d.donados + d.guardados === 0 && d.recuperado === 0 && d.perdido === 0;
  const pct = d.pct_recuperado;
  return (
    <Seccion titulo="Merma recuperada" mensajes={d.mensajes}>
      {vacio ? (
        <Vacio titulo="Todavía no marcaste ningún sobrante" texto="Para marcar un sobrante como reutilizado ve a Menú → Sobrantes." />
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-2">
            <Dato etiqueta="Recuperado" valor={dinero(d.recuperado)} tono="text-ok" />
            <Dato etiqueta="Perdido" valor={dinero(d.perdido)} tono="text-bad" />
          </div>
          <div>
            <div className="mb-1 flex justify-between text-sm"><span>Parte recuperada</span><span className="font-medium tabular-nums">{textoPct(pct)}</span></div>
            <div className="h-3 rounded-full bg-line" role="img"
              aria-label={pct === null ? "Todavía no hay proporción recuperada" : `Recuperaste el ${textoPct(pct)} de lo que sobró`}>
              <div className="h-3 rounded-full bg-ok" style={{ width: `${pct === null ? 0 : anchoBarra(pct, 100)}%` }} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Dato etiqueta="Reutilizados" valor={d.reutilizados} />
            <Dato etiqueta="Desperdiciados" valor={d.desperdiciados} />
            <Dato etiqueta="Donados" valor={d.donados} />
            <Dato etiqueta="Esperando destino" valor={d.guardados} nota="guardados sin marcar" />
          </div>
        </>
      )}
      <p className="text-sm text-muted">Para marcar un sobrante como reutilizado ve a Menú → Sobrantes.</p>
    </Seccion>
  );
}

function Produccion({ d }: { d: AnalisisProduccion }) {
  const maxServ = Math.max(0, ...d.por_servicio.map((s) => s.producido));
  return (
    <Seccion titulo="Producido contra vendido" periodo={d.periodo} demo={d.demo} mensajes={d.mensajes}>
      {d.producido === 0 && d.por_plato.length === 0 ? (
        <Vacio titulo="No hay producción en estas fechas" texto={sinDatos(d.mensajes, "Prueba con otras fechas o toca «Todo».")} />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
            <Dato etiqueta="Producido" valor={d.producido} />
            <Dato etiqueta="Vendido" valor={d.vendido} />
            <Dato etiqueta="Sobró" valor={d.sobrante} />
            <Dato etiqueta="Sobrante" valor={textoPct(d.pct_sobrante)} tono="text-warn" />
            <Dato etiqueta="Costo de lo que sobró" valor={dinero(d.costo_sobrante)} tono="text-bad" />
          </div>
          <div>
            <h3 className="mb-2 font-medium">Por servicio</h3>
            <ul className="space-y-3" aria-label="Producido y vendido por servicio">
              {d.por_servicio.map((s) => (
                <li key={s.servicio}>
                  <div className="flex flex-wrap justify-between gap-2 text-sm">
                    <span className="font-medium">{NOMBRE_COMIDA[s.servicio] ?? s.servicio}</span>
                    <span className="tabular-nums text-muted">Producido {s.producido} · Vendido {s.vendido} · Sobra {textoPct(s.pct_sobrante)}</span>
                  </div>
                  <div className="mt-1 space-y-1" aria-hidden>
                    <div className="h-2.5 rounded-full bg-line"><div className="h-2.5 rounded-full bg-brand/40" style={{ width: `${anchoBarra(s.producido, maxServ)}%` }} /></div>
                    <div className="h-2.5 rounded-full bg-line"><div className="h-2.5 rounded-full bg-brand" style={{ width: `${anchoBarra(s.vendido, maxServ)}%` }} /></div>
                  </div>
                </li>
              ))}
            </ul>
            <p className="mt-2 text-xs text-muted">Barra clara: producido. Barra fuerte: vendido.</p>
          </div>
          <div>
            <h3 className="mb-2 font-medium">Platos que más sobran</h3>
            {d.por_plato.length === 0 ? <p className="text-sm text-muted">Sin datos.</p> : (
              <Tabla>
                <thead><tr><Th>Plato</Th><Th className="text-right">Producido</Th><Th className="text-right">Vendido</Th><Th className="text-right">Sobró</Th>
                  <Th className="text-right">% sobrante</Th><Th className="text-right">Costo de lo que sobró</Th></tr></thead>
                <tbody>
                  {d.por_plato.map((p) => (
                    <tr key={p.receta_id ?? p.plato}>
                      <Td className="font-medium">{p.plato}</Td><Td className="text-right tabular-nums">{p.producido}</Td><Td className="text-right tabular-nums">{p.vendido}</Td>
                      <Td className="text-right tabular-nums">{p.sobrante}</Td><Td className="text-right tabular-nums">{textoPct(p.pct_sobrante)}</Td>
                      <Td className="text-right tabular-nums">{p.costo_sobrante === null ? "-" : dinero(p.costo_sobrante)}</Td>
                    </tr>
                  ))}
                </tbody>
              </Tabla>
            )}
          </div>
        </>
      )}
    </Seccion>
  );
}

const claseMargen = { ok: "ok", warn: "warn", bad: "bad" } as const;

function TablaRent({ titulo, filas }: { titulo: string; filas: PlatoRent[] }) {
  return (
    <div>
      <h3 className="mb-2 font-medium">{titulo}</h3>
      {filas.length === 0 ? <p className="text-sm text-muted">Sin datos.</p> : (
        <Tabla>
          <thead><tr><Th>Plato</Th><Th className="text-right">Vendidos</Th><Th className="text-right">Ingresos</Th><Th className="text-right">Costo</Th>
            <Th className="text-right">Ganancia</Th><Th>Margen</Th></tr></thead>
          <tbody>
            {filas.map((p) => {
              const n = nivelMargen(p.margen_pct);
              return (
                <tr key={p.receta_id ?? p.plato}>
                  <Td className="font-medium">{p.plato}</Td><Td className="text-right tabular-nums">{p.vendido}</Td>
                  <Td className="text-right tabular-nums">{dinero(p.ingresos)}</Td><Td className="text-right tabular-nums">{dinero(p.costo)}</Td>
                  <Td className={cx("text-right tabular-nums", p.ganancia < 0 && "text-bad")}>{dinero(p.ganancia)}</Td>
                  <Td>{n ? <Badge nivel={claseMargen[n]}>{textoPct(p.margen_pct)}</Badge> : <span className="text-muted">Sin costo</span>}</Td>
                </tr>
              );
            })}
          </tbody>
        </Tabla>
      )}
    </div>
  );
}

function Rentables({ d }: { d: AnalisisRentables }) {
  return (
    <Seccion titulo="Platos que más dejan" periodo={d.periodo} demo={d.demo} mensajes={d.mensajes}>
      {d.mas_ganan.length === 0 && d.menos_ganan.length === 0 ? (
        <Vacio titulo="No hay ventas en estas fechas" texto={sinDatos(d.mensajes, "Prueba con otras fechas o toca «Todo».")} />
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-2">
            <Dato etiqueta="Ingresos" valor={dinero(d.ingresos)} />
            <Dato etiqueta="Ganancia" valor={dinero(d.ganancia)} tono={d.ganancia < 0 ? "text-bad" : "text-ok"} />
          </div>
          <TablaRent titulo="Los que más dejan" filas={d.mas_ganan} />
          <TablaRent titulo="Los que menos dejan" filas={d.menos_ganan} />
        </>
      )}
      {d.sin_costo.length > 0 && (
        <p role="note" className="rounded-xl border border-warn/40 bg-warn/10 p-3 text-sm text-warn">
          No pude calcular la ganancia de {d.sin_costo.length} {d.sin_costo.length === 1 ? "plato" : "platos"} porque no tienen receta con costo: {d.sin_costo.join(", ")}.
        </p>
      )}
    </Seccion>
  );
}

function PerdidaPorTurno({ desde, hasta }: { desde: string; hasta: string }) {
  const q = useQuery({ queryKey: ["balance-tendencia", desde, hasta], queryFn: () => api.tendenciaBalance({ desde, hasta }), placeholderData: (p) => p });
  if (q.error) return <ErrorCaja error={q.error} onReintentar={() => q.refetch()} />;
  if (!q.data) return <Skeleton className="h-56 w-full" />;
  const d = q.data;
  return (
    <Seccion titulo="Pérdida sin explicar por turno" mensajes={d.mensajes}>
      {d.turnos.length === 0 ? (
        <Vacio titulo="No hay balances en estas fechas" texto={sinDatos(d.mensajes, "Cuando se firmen informes de turno con entregas de bodega, aparecerán aquí.")} />
      ) : (
        <>
          <div>
            <h3 className="mb-2 font-medium">Por turno</h3>
            <Tabla>
              <thead><tr><Th>Turno</Th><Th className="text-right">Promedio sin explicar</Th><Th className="text-right">Alarmas</Th></tr></thead>
              <tbody>
                {d.por_turno.map((t) => (
                  <tr key={t.turno}>
                    <Td className="font-medium">{nombreTurno(t.turno)}</Td>
                    <Td className="text-right tabular-nums">{pct(t.promedio_pct)}</Td>
                    <Td className={cx("text-right tabular-nums", t.alarmas > 0 && "text-bad")}>{t.alarmas}</Td>
                  </tr>
                ))}
              </tbody>
            </Tabla>
          </div>
          <div>
            <h3 className="mb-2 font-medium">Turno por turno</h3>
            <Tabla>
              <thead><tr><Th>Fecha</Th><Th>Turno</Th><Th>Estado</Th><Th className="text-right">Entró</Th><Th className="text-right">Sin explicar</Th><Th className="text-right">%</Th><Th className="text-right">Dinero</Th></tr></thead>
              <tbody>
                {d.turnos.map((f) => (
                  <tr key={`${f.fecha}-${f.turno}`}>
                    <Td>{fechaEnFrase(f.fecha)}</Td><Td>{nombreTurno(f.turno)}</Td>
                    <Td><span className={cx("inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium", colorEstado(f.estado).caja, colorEstado(f.estado).texto)}>
                      <span className={cx("h-1.5 w-1.5 rounded-full", colorEstado(f.estado).punto)} aria-hidden />{etiquetaEstado(f.estado)}</span></Td>
                    <Td className="text-right tabular-nums">{kg(f.entro_kg)}</Td><Td className="text-right tabular-nums">{kg(f.sin_explicar_kg)}</Td>
                    <Td className="text-right tabular-nums">{pct(f.sin_explicar_pct)}</Td>
                    <Td className="text-right tabular-nums">{f.sin_explicar_dinero === null ? "—" : dinero(f.sin_explicar_dinero)}</Td>
                  </tr>
                ))}
              </tbody>
            </Tabla>
          </div>
        </>
      )}
    </Seccion>
  );
}

function Esqueleto() {
  return (
    <div className="space-y-6" role="status" aria-label="Cargando el análisis">
      {[0, 1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-56 w-full" />)}
    </div>
  );
}

export function Analisis() {
  const atajos = useMemo(() => atajosFechas(new Date()), []);
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const mal = desde !== "" && hasta !== "" && desde > hasta;
  const q = useQuery({
    queryKey: ["analisis", desde, hasta],
    queryFn: () => api.analisis({ desde, hasta }),
    enabled: !mal,
    placeholderData: (p) => p,
  });
  const campo = "rounded-xl border border-line bg-bg px-3 py-2";
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end gap-4 rounded-2xl border border-line bg-surface p-4">
        <div><label htmlFor="an-desde" className="mb-1 block text-sm text-muted">Desde</label>
          <input id="an-desde" type="date" value={desde} max={hasta || undefined} onChange={(e) => setDesde(e.target.value)} className={campo} /></div>
        <div><label htmlFor="an-hasta" className="mb-1 block text-sm text-muted">Hasta</label>
          <input id="an-hasta" type="date" value={hasta} min={desde || undefined} onChange={(e) => setHasta(e.target.value)} className={campo} /></div>
        <div role="group" aria-label="Atajos de fechas" className="flex flex-wrap gap-2">
          {atajos.map((a) => (
            <Button key={a.id} type="button" aria-pressed={desde === a.desde && hasta === a.hasta}
              className={cx(desde === a.desde && hasta === a.hasta && "border-brand text-brand")}
              onClick={() => { setDesde(a.desde); setHasta(a.hasta); }}>{a.nombre}</Button>
          ))}
        </div>
        {mal && <p role="alert" className="w-full text-sm text-bad">La fecha «Desde» no puede ser después de «Hasta».</p>}
      </div>
      <p className="text-sm text-muted">Cada bloque dice de qué fechas son sus datos. Las mermas y las ventas no cubren los mismos meses.</p>
      {q.error ? <ErrorCaja error={q.error} onReintentar={() => q.refetch()} /> : !q.data ? (mal ? null : <Esqueleto />) : (
        <div className={cx("space-y-6", q.isFetching && "opacity-60")} aria-busy={q.isFetching}>
          <Mermas d={q.data.mermas} />
          <Recuperacion d={q.data.recuperacion} />
          <Produccion d={q.data.produccion} />
          <Rentables d={q.data.rentables} />
          <CostoReal d={q.data.costo_real} />
          <PerdidaPorTurno desde={desde} hasta={hasta} />
        </div>
      )}
    </div>
  );
}
