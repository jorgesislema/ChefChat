import { Link } from "react-router-dom";
import type { CostoReal as DatosCostoReal } from "../../lib/api";
import { anchoBarra, textoPct } from "../../lib/analisis";
import { ETIQUETAS_BARRA, partesBarra, type ParteBarra } from "../../lib/compras";
import { filaUsado } from "../../lib/conteo";
import { dinero, fechaEnFrase } from "../../lib/format";
import { cx } from "../ui/ui";
import { Dato, Seccion } from "./Graficos";

const COLOR: Record<ParteBarra["clave"], string> = {
  vendido: "bg-ok", sobreproduccion: "bg-warn", merma_registrada: "bg-muted", sin_explicar: "bg-bad",
};

function BarraApilada({ d }: { d: NonNullable<DatosCostoReal["desglose"]> }) {
  const { partes, gastoMenor } = partesBarra(d);
  const resumen = "De lo que gastaste: " + (partes.length === 0 ? "sin montos" : partes.map((p) => `${p.etiqueta} ${dinero(p.monto)}`).join("; "));
  return (
    <div>
      <h3 className="mb-2 font-medium">¿En qué se fue lo que gastaste?</h3>
      {partes.length > 0 && (
        <div role="img" aria-label={resumen} className="flex h-5 w-full overflow-hidden rounded-full bg-line">
          {partes.map((p) => <div key={p.clave} className={COLOR[p.clave]} style={{ width: `${p.pct}%` }} />)}
        </div>
      )}
      <ul className="mt-3 grid gap-2 text-sm sm:grid-cols-2" aria-label="Leyenda de la barra">
        {(["vendido", "sobreproduccion", "merma_registrada", "sin_explicar"] as const).map((k) => {
          const monto = d[k];
          const parte = partes.find((p) => p.clave === k);
          return (
            <li key={k} className="flex items-baseline justify-between gap-3">
              <span className="flex items-center gap-2">
                <span className={cx("h-3 w-3 shrink-0 rounded-sm", COLOR[k])} aria-hidden />
                {ETIQUETAS_BARRA[k]}
              </span>
              <span className="tabular-nums text-muted">{dinero(monto)}{parte ? ` · ${textoPct(parte.pct)}` : ""}</span>
            </li>
          );
        })}
      </ul>
      {gastoMenor && <p className="mt-2 text-sm text-ok">Gastaste menos de lo esperado: la parte «sin explicar» es negativa y por eso no se dibuja.</p>}
    </div>
  );
}

function BarraObjetivo({ real, objetivo }: { real: number | null; objetivo: number }) {
  const max = Math.max(real ?? 0, objetivo) * 1.25;
  const encima = real !== null && real > objetivo;
  const resumen = real === null
    ? `Todavía no hay porcentaje real. El objetivo es ${textoPct(objetivo)} de las ventas.`
    : `Gastaste el ${textoPct(real)} de las ventas. El objetivo es ${textoPct(objetivo)}.`;
  return (
    <div>
      <h3 className="mb-2 font-medium">Gasto como parte de las ventas</h3>
      <div role="img" aria-label={resumen} className="relative h-5 w-full rounded-full bg-line">
        <div className={cx("h-5 rounded-full", encima ? "bg-bad" : "bg-ok")} style={{ width: `${anchoBarra(real ?? 0, max)}%` }} />
        <div className="absolute -top-1 h-7 w-0.5 bg-ink" style={{ left: `${anchoBarra(objetivo, max)}%` }} />
      </div>
      <p className="mt-2 text-sm text-muted">
        Real: <span className="font-medium text-ink">{textoPct(real)}</span> de las ventas. La línea marca el objetivo: {textoPct(objetivo)}.
      </p>
    </div>
  );
}

function MetodoCosto({ d }: { d: DatosCostoReal }) {
  const f = filaUsado(d);
  return (
    <div className="space-y-2">
      {d.metodo === "conteo" ? (
        <span className="inline-flex items-center gap-1.5 rounded-full border border-ok/40 bg-ok/15 px-2.5 py-0.5 text-xs font-medium text-ok">Exacto: con conteos de inventario</span>
      ) : (
        <p className="flex flex-wrap items-center gap-3">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-warn/40 bg-warn/15 px-2.5 py-0.5 text-xs font-medium text-warn">Aproximado: solo con compras</span>
          <Link to="/inventario?vista=conteo" className="text-sm font-medium text-brand underline">Hacer un conteo</Link>
        </p>
      )}
      {f && (
        <p className="text-sm text-muted">
          Inventario al {fechaEnFrase(f.fechaInicial)}: <span className="text-ink">{dinero(f.inicial)}</span> + Compras: <span className="text-ink">{dinero(f.comprado)}</span>
          {" "}− Inventario al {fechaEnFrase(f.fechaFinal)}: <span className="text-ink">{dinero(f.final)}</span> = Usaste: <span className="font-medium text-ink">{dinero(f.usado)}</span>
        </p>
      )}
    </div>
  );
}

export function CostoReal({ d }: { d: DatosCostoReal }) {
  return (
    <Seccion titulo="Costo real contra lo esperado" periodo={{ desde: d.periodo.desde, hasta: d.periodo.hasta }} demo={d.demo} mensajes={d.mensajes}>
      <MetodoCosto d={d} />
      {d.desglose === null ? (
        <p className="text-sm">
          Para calcular esto hacen falta compras y ventas en las mismas fechas.{" "}
          <Link to="/compras" className="font-medium text-brand underline">Registrar compras</Link>
        </p>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-3">
            <Dato etiqueta="Lo que gastaste" valor={dinero(d.real)} nota={`${textoPct(d.real_pct)} de las ventas`} />
            <Dato etiqueta="Lo que debió costar" valor={dinero(d.teorico)} nota={`${textoPct(d.teorico_pct)} de las ventas`} />
            <Dato etiqueta="Diferencia" valor={dinero(d.diferencia)} tono={d.diferencia > 0 ? "text-bad" : "text-ok"}
              nota={d.diferencia > 0 ? `Gastaste de más · ${textoPct(d.diferencia_pct)}` : `Dentro de lo esperado · ${textoPct(d.diferencia_pct)}`} />
          </div>
          <BarraApilada d={d.desglose} />
          <BarraObjetivo real={d.real_pct} objetivo={d.objetivo_pct} />
        </>
      )}
    </Seccion>
  );
}
