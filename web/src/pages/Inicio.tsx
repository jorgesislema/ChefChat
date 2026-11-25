import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { abrirChat } from "../lib/chatStore";
import { Foquito } from "../components/Foquito";
import { AlertOctagon, CalendarClock, CalendarDays, DollarSign, GraduationCap, UtensilsCrossed, type LucideIcon } from "lucide-react";
import { useResumen } from "../hooks/useResumen";
import { Badge, Card, ErrorCaja, Pagina, Skeleton, Vacio, cx, tono } from "../components/ui/ui";
import { diasRestantes, dinero, etiquetaDias, fechaLarga, semaforo, type Semaforo } from "../lib/format";

function Tarjeta({ titulo, valor, nivel, Icono, onClick, nota }: {
  titulo: string; valor: string; nivel: Semaforo; Icono: LucideIcon; onClick: () => void; nota: string;
}) {
  return (
    <button onClick={onClick} aria-label={`${titulo}: ${valor}. ${nota}`}
      className="rise group rounded-2xl border border-line bg-surface p-5 text-left transition hover:-translate-y-0.5 hover:border-brand">
      <div className="flex items-center justify-between">
        <span className="font-medium text-muted">{titulo}</span>
        <span className={cx("rounded-xl border p-2", tono[nivel])}><Icono size={20} aria-hidden /></span>
      </div>
      <p className={cx("mt-3 whitespace-nowrap text-3xl font-bold tabular-nums", { bad: "text-bad", warn: "text-warn", ok: "text-ok" }[nivel])}>{valor}</p>
      <p className="mt-1 text-sm text-muted">{nota}</p>
    </button>
  );
}

export default function Inicio() {
  const { data, isLoading, error, refetch } = useResumen();
  const nav = useNavigate();
  const cocinar = useQuery({ queryKey: ["menu-cocinar", 1, []], queryFn: () => api.menuCocinar(1) });

  if (error) return <Pagina titulo="Inicio"><ErrorCaja error={error} onReintentar={() => refetch()} /></Pagina>;
  if (isLoading || !data)
    return (
      <Pagina titulo="Inicio">
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-36" />)}</div>
        <Skeleton className="h-64" />
      </Pagina>
    );

  const s = data.vencen_7_dias.lotes, v = data.ya_vencidos.lotes, d = data.vencen_diciembre.lotes;
  const maxMerma = Math.max(...data.mermas_por_motivo.map((m) => m.costo), 1);
  const evals = data.examenes.por_persona;
  const aprobadas = evals.filter((e) => e.aprobado === 1).length;
  const activos = data.personal.reduce((a, p) => a + p.n, 0);
  const nVencen = cocinar.data?.por_vencer.length ?? 0;
  const textoCocinar = cocinar.isError ? "No pude revisar lo que vence mañana." : !cocinar.data ? "Revisando…"
    : nVencen === 0 ? "Nada vence mañana" : `${nVencen} ${nVencen === 1 ? "producto vence" : "productos vencen"} mañana`;
  const lotes = (n: number) => (n === 1 ? "1 lote" : `${n} lotes`);

  return (
    <Pagina titulo="Hola, ¿cómo va el restaurante?" subtitulo={fechaLarga(data.fecha)}>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Tarjeta titulo="Vencen esta semana" valor={String(s)} nivel={s ? "warn" : "ok"} Icono={CalendarClock}
          nota={s ? `${lotes(s)} por revisar` : "Todo en orden"} onClick={() => nav("/inventario?vista=vencimientos&rango=1")} />
        <Tarjeta titulo="Ya vencidos" valor={String(v)} nivel={v ? "bad" : "ok"} Icono={AlertOctagon}
          nota={v ? `${lotes(v)}: sácalos del almacén` : "No hay productos vencidos"}
          onClick={() => abrirChat("¿Qué productos ya están vencidos?")} />
        <Tarjeta titulo="Vencen en diciembre" valor={String(d)} nivel={d ? "warn" : "ok"} Icono={CalendarDays}
          nota={d ? `${lotes(d)} para planificar` : "Nada por vencer"} onClick={() => nav("/inventario?vista=vencimientos&rango=dic")} />
        <Tarjeta titulo="Costo de mermas" valor={dinero(data.mermas_total)} nivel={data.mermas_total ? "warn" : "ok"} Icono={DollarSign}
          nota="Principales 5 motivos" onClick={() => nav("/mermas")} />
      </div>

      <Link to="/menu?pestana=cocinar" aria-label={`Qué cocinar mañana: ${textoCocinar}`}
        className="flex items-center gap-4 rounded-2xl border border-line bg-surface p-4 transition hover:border-brand">
        <span className="rounded-xl border border-line p-2 text-brand"><UtensilsCrossed size={20} aria-hidden /></span>
        <span className="flex-1">
          <span className="block font-medium">Qué cocinar mañana</span>
          <span className="block text-sm text-muted">{textoCocinar}</span>
        </span>
        {nVencen > 0 && <Foquito dias={1} />}
      </Link>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <h2 className="mb-3 text-lg font-semibold">Lo que vence primero</h2>
          {data.vencen_7_dias.items.length === 0 ? (
            <Vacio titulo="Nada vence esta semana" texto="Cuando algún producto esté cerca de vencer, aparecerá aquí." />
          ) : (
            <ul className="divide-y divide-line">
              {data.vencen_7_dias.items.map((it, i) => {
                const dias = diasRestantes(it.vence);
                return (
                  <li key={`${it.lote}-${i}`} className="flex items-center justify-between gap-3 py-3">
                    <div className="min-w-0">
                      <p className="flex items-center gap-2 truncate font-medium">{it.producto}<Foquito dias={dias} tipo={it.tipo} /></p>
                      <p className="text-sm text-muted">{it.cantidad} {it.unidad}</p>
                    </div>
                    <Badge nivel={semaforo(dias)}>{etiquetaDias(dias)}</Badge>
                  </li>
                );
              })}
            </ul>
          )}
        </Card>

        <Card>
          <h2 className="mb-3 text-lg font-semibold">Mermas por motivo</h2>
          {data.mermas_por_motivo.length === 0 ? (
            <Vacio titulo="Sin mermas registradas" />
          ) : (
            <ul className="space-y-3">
              {data.mermas_por_motivo.map((m) => (
                <li key={m.motivo}>
                  <div className="mb-1 flex justify-between text-sm">
                    <span className="capitalize">{m.motivo}</span>
                    <span className="tabular-nums text-muted">{dinero(m.costo)} · {m.veces} {m.veces === 1 ? "vez" : "veces"}</span>
                  </div>
                  <div className="h-3 rounded-full bg-line" role="img" aria-label={`${m.motivo}: ${dinero(m.costo)}`}>
                    <div className="h-3 rounded-full bg-brand transition-all" style={{ width: `${(m.costo / maxMerma) * 100}%` }} />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card>
        <div className="flex flex-wrap items-center gap-4">
          <span className="rounded-xl border border-line p-3 text-brand"><GraduationCap aria-hidden /></span>
          <div className="flex-1">
            <h2 className="text-lg font-semibold">Capacitación</h2>
            <p className="text-sm text-muted">
              {evals.length
                ? `${aprobadas} de ${evals.length} evaluaciones aprobadas · ${activos} personas en el equipo`
                : `Aún no hay evaluaciones. ${activos} personas en el equipo.`}
            </p>
          </div>
          <Link to="/capacitacion" className="rounded-xl bg-brand px-4 py-2 text-sm font-semibold text-black hover:brightness-110">Ir a capacitación</Link>
        </div>
      </Card>
    </Pagina>
  );
}

