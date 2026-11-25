import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { api, type Balance as DatosBalance, type Turno } from "../../lib/api";
import { colorEstado, etiquetaEstado, kg, pct, tramosBarra } from "../../lib/balance";
import { dinero } from "../../lib/format";
import { Button, Card, Cargando, ErrorCaja, Tabla, Td, Th, cx } from "../ui/ui";
import { Dato } from "../analisis/Graficos";
import { ConfirmarQuitar } from "../edicion/comun";
import { DialogoMerma, DialogoMovimiento, DialogoSalida } from "./BalanceDialogos";

const PRIMEROS = 8;

type Abierto = null | "entrega" | "devolucion" | "merma" | "comida_personal" | "residuo_limpieza";
type Quitar = { tipo: "movimiento" | "salida"; id: number; texto: string } | null;

interface Props { fecha: string; turno: Turno; firmado: boolean; congelado?: DatosBalance }

export function Balance({ fecha, turno, firmado, congelado }: Props) {
  const qc = useQueryClient();
  const usaFoto = firmado && !!congelado;
  const q = useQuery({ queryKey: ["balance", fecha, turno], queryFn: () => api.balance(fecha, turno), enabled: !usaFoto });
  const [abierto, setAbierto] = useState<Abierto>(null);
  const [quitar, setQuitar] = useState<Quitar>(null);
  const [verTodos, setVerTodos] = useState(false);

  const b = usaFoto ? congelado : q.data;
  const puedeAnotar = !firmado;
  const refrescar = () => qc.invalidateQueries({ queryKey: ["balance", fecha, turno] });

  if (!b) {
    return (
      <Card className="space-y-3">
        <h2 className="text-lg font-semibold">Balance del turno</h2>
        {q.error ? <ErrorCaja error={q.error} onReintentar={() => q.refetch()} /> : <Cargando filas={3} />}
      </Card>
    );
  }

  const c = colorEstado(b.estado);
  const k = b.kg;
  const falta = k.sin_explicar > 0;
  const tramos = tramosBarra(k);
  const lineas = verTodos ? b.por_ingrediente : b.por_ingrediente.slice(0, PRIMEROS);

  return (
    <Card className="space-y-5">
      <h2 className="text-lg font-semibold">Balance del turno</h2>

      <div className={cx("rounded-2xl border p-4", c.caja)}>
        <p className={cx("flex items-center gap-3 text-2xl font-bold", c.texto)} role="status">
          <span className={cx("h-4 w-4 rounded-full", c.punto)} aria-hidden /> {etiquetaEstado(b.estado)}
        </p>
        {b.mensajes.length > 0 && <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">{b.mensajes.map((m, i) => <li key={i}>{m}</li>)}</ul>}
      </div>
      {b.avisos.length > 0 && (
        <ul className="list-disc space-y-1 rounded-xl border border-warn/40 bg-warn/10 p-3 pl-7 text-sm text-warn">{b.avisos.map((m, i) => <li key={i}>{m}</li>)}</ul>
      )}

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <Dato etiqueta="Entró" valor={kg(k.entro)} nota={`entregado ${kg(k.entregado)} − devuelto ${kg(k.devuelto)}`} />
        <Dato etiqueta="Salió bueno" valor={kg(k.salio_bueno)} />
        <Dato etiqueta="Pérdida normal" valor={kg(k.perdida_normal)} />
        <Dato etiqueta="Anotado" valor={kg(k.anotado)}
          nota={`merma ${kg(k.merma)} · personal ${kg(k.comida_personal)} · limpieza ${kg(k.residuo_limpieza)} · muestras ${kg(k.muestra)} · otro ${kg(k.otro)}`} />
        <Dato etiqueta={falta ? "Sin explicar (falta)" : "Sin explicar"} valor={kg(k.sin_explicar)} tono={b.estado === "alarma" ? "text-bad" : undefined}
          nota={`${pct(b.sin_explicar_pct)} · ${b.sin_explicar_dinero === null ? "sin costo" : dinero(b.sin_explicar_dinero)}`} />
      </div>

      {tramos.length > 0 && (
        <div>
          <h3 className="mb-2 font-medium">¿A dónde fue lo que entró?</h3>
          <div className="flex h-4 overflow-hidden rounded-full bg-line" role="img"
            aria-label={`Reparto de ${kg(k.entro)}: ${tramos.map((t) => `${t.etiqueta} ${kg(t.kg)}`).join(", ")}`}>
            {tramos.filter((t) => t.pct > 0).map((t) => <div key={t.clave} className={t.color} style={{ width: `${t.pct}%` }} />)}
          </div>
          <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm" aria-label="Leyenda">
            {tramos.map((t) => (
              <li key={t.clave} className="inline-flex items-center gap-1.5">
                <span className={cx("h-2.5 w-2.5 rounded-full", t.color)} aria-hidden /> {t.etiqueta}: {kg(t.kg)}
              </li>
            ))}
          </ul>
          {k.sin_explicar < 0 && <p className="mt-1 text-sm text-muted">Sobran {kg(-k.sin_explicar)}: salió más de lo que entró.</p>}
        </div>
      )}

      {puedeAnotar && (
        <div className="no-print flex flex-wrap gap-2">
          <Button type="button" onClick={() => setAbierto("entrega")}>Entrega de bodega</Button>
          <Button type="button" onClick={() => setAbierto("devolucion")}>Devolución a bodega</Button>
          <Button type="button" onClick={() => setAbierto("merma")}>Merma pesada</Button>
          <Button type="button" onClick={() => setAbierto("comida_personal")}>Comida del personal</Button>
          <Button type="button" onClick={() => setAbierto("residuo_limpieza")}>Residuo de limpieza</Button>
        </div>
      )}

      <div className="space-y-2">
        <h3 className="font-medium">Por ingrediente</h3>
        {b.por_ingrediente.length === 0 ? <p className="text-sm text-muted">Todavía no hay ingredientes para comparar.</p> : (
          <>
            <Tabla>
              <thead><tr>
                <Th>Producto</Th><Th className="text-right">Entregado neto</Th><Th className="text-right">Uso según receta</Th>
                <Th className="text-right">Merma</Th><Th className="text-right">Diferencia</Th><Th className="text-right">Valor</Th>
              </tr></thead>
              <tbody>
                {lineas.map((l) => {
                  const grande = l.diferencia > 0 && (l.diferencia_pct ?? 0) > b.tolerancia_pct;
                  return (
                    <tr key={l.producto_id}>
                      <Td className="font-medium">{l.producto}</Td>
                      <Td className="text-right tabular-nums">{l.sin_entrega ? <span className="text-muted">Sin entrega</span> : kg(l.neto)}</Td>
                      <Td className="text-right tabular-nums">{kg(l.uso_receta)}</Td>
                      <Td className="text-right tabular-nums">{kg(l.merma)}</Td>
                      <Td className={cx("text-right tabular-nums", grande && "font-semibold text-bad")}>
                        {l.calculable ? <>{kg(l.diferencia)}{l.diferencia_pct !== null && <span className="block text-xs">{pct(l.diferencia_pct)}</span>}</> : "—"}
                      </Td>
                      <Td className="text-right tabular-nums">{l.valor_diferencia === null ? "—" : dinero(l.valor_diferencia)}</Td>
                    </tr>
                  );
                })}
              </tbody>
            </Tabla>
            <p className="text-xs text-muted">Diferencia positiva = falta. Negativa = sobra.</p>
            {b.por_ingrediente.length > PRIMEROS && (
              <Button type="button" onClick={() => setVerTodos((v) => !v)}>{verTodos ? "Ver menos" : `Ver todos (${b.por_ingrediente.length})`}</Button>
            )}
          </>
        )}
      </div>

      <div className="space-y-2">
        <h3 className="font-medium">Por unidades</h3>
        <p className="text-sm text-muted">Recibido lo cuenta otra persona (mostrador o despacho). Se anota en «Producido y vendido».</p>
        {b.por_plato.length === 0 ? <p className="text-sm text-muted">No hay platos anotados.</p> : (
          <Tabla>
            <thead><tr><Th>Plato</Th><Th className="text-right">Producido</Th><Th className="text-right">Recibido</Th><Th className="text-right">Vendido</Th><Th className="text-right">Pérdidas</Th></tr></thead>
            <tbody>
              {b.por_plato.map((p, i) => (
                <tr key={`${p.receta_id ?? p.plato}-${i}`}>
                  <Td className="font-medium">{p.plato ?? "Sin nombre"}</Td>
                  <Td className="text-right tabular-nums">{p.producido}</Td>
                  <Td className="text-right tabular-nums">{p.recibido ?? "—"}</Td>
                  <Td className="text-right tabular-nums">{p.vendido}</Td>
                  <Td className={cx("text-right tabular-nums", (p.perdidas_unidades ?? 0) > 0 && "text-bad")}>{p.perdidas_unidades ?? "—"}</Td>
                </tr>
              ))}
            </tbody>
          </Tabla>
        )}
      </div>

      <Lista titulo="Entregas y devoluciones de bodega" vacio="No se anotó ninguna.">
        {b.movimientos.map((m) => {
          const texto = `${m.tipo === "entrega" ? "Entrega" : "Devolución"}: ${m.producto ?? "Sin nombre"}, ${m.cantidad} ${m.unidad}`;
          return (
            <Fila key={m.id} texto={texto} detalle={[m.entrego && `entregó ${m.entrego}`, m.recibio && `recibió ${m.recibio}`].filter(Boolean).join(" · ")}
              quitar={puedeAnotar ? () => setQuitar({ tipo: "movimiento", id: m.id, texto }) : undefined} />
          );
        })}
      </Lista>
      <Lista titulo="Salidas anotadas" vacio="No se anotó ninguna.">
        {b.salidas.map((s) => {
          const texto = `${s.nombre_tipo}: ${kg(s.kg)}`;
          return (
            <Fila key={s.id} texto={texto} detalle={[s.producto, s.nota, s.persona].filter(Boolean).join(" · ")}
              quitar={puedeAnotar ? () => setQuitar({ tipo: "salida", id: s.id, texto }) : undefined} />
          );
        })}
      </Lista>
      <Lista titulo="Mermas del turno" vacio="No se anotó ninguna.">
        {b.mermas.map((m) => (
          <Fila key={m.id} texto={`${m.producto}: ${m.cantidad} ${m.unidad}`}
            detalle={[m.motivo, m.kg !== null && kg(m.kg), m.costo !== null && dinero(m.costo)].filter(Boolean).join(" · ")} />
        ))}
      </Lista>

      {abierto === "entrega" && <DialogoMovimiento tipo="entrega" fecha={fecha} turno={turno} onCerrar={() => setAbierto(null)} />}
      {abierto === "devolucion" && <DialogoMovimiento tipo="devolucion" fecha={fecha} turno={turno} onCerrar={() => setAbierto(null)} />}
      {abierto === "merma" && <DialogoMerma fecha={fecha} turno={turno} onCerrar={() => setAbierto(null)} />}
      {(abierto === "comida_personal" || abierto === "residuo_limpieza") && (
        <DialogoSalida tipo={abierto} fecha={fecha} turno={turno} onCerrar={() => setAbierto(null)} />
      )}
      {quitar && (
        <ConfirmarQuitar titulo="Quitar lo anotado" texto={`¿Quitar «${quitar.texto}»?`} confirmar="Sí, quitar" alCerrar={() => setQuitar(null)}
          alConfirmar={async () => {
            await (quitar.tipo === "movimiento" ? api.quitarMovimiento(quitar.id) : api.quitarSalida(quitar.id));
            await refrescar();
          }} />
      )}
    </Card>
  );
}

function Lista({ titulo, vacio, children }: { titulo: string; vacio: string; children: React.ReactNode[] }) {
  return (
    <div>
      <h3 className="mb-1 font-medium">{titulo}</h3>
      {children.length === 0 ? <p className="text-sm text-muted">{vacio}</p> : <ul className="divide-y divide-line rounded-xl border border-line" aria-label={titulo}>{children}</ul>}
    </div>
  );
}

function Fila({ texto, detalle, quitar }: { texto: string; detalle?: string; quitar?: () => void }) {
  return (
    <li className="flex items-center justify-between gap-3 p-3 text-sm">
      <span><span className="font-medium">{texto}</span>{detalle && <span className="block text-muted">{detalle}</span>}</span>
      {quitar && (
        <Button type="button" variante="peligro" aria-label={`Quitar ${texto}`} onClick={quitar}><Trash2 size={14} aria-hidden /> Quitar</Button>
      )}
    </li>
  );
}
