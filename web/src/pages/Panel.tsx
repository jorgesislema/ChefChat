import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Pencil, Trash2 } from "lucide-react";
import { api, type Edicion, type EstadoPregunta, type PreguntaBanco } from "../lib/api";
import { Badge, Button, Card, Cargando, Dialogo, ErrorCaja, Pagina, Pestanas, Tabla, Td, Th, Vacio, cx } from "../components/ui/ui";
import type { Semaforo } from "../lib/format";
import { Analisis } from "../components/analisis/Analisis";
import { Cambios } from "../components/analisis/Cambios";

const nivelJev = (p: number | null): Semaforo => (p === null ? "warn" : p >= 0.9 ? "ok" : p >= 0.75 ? "warn" : "bad");

function Editar({ p, onCerrar, onGuardar, cargando, error }: {
  p: PreguntaBanco; onCerrar: () => void; onGuardar: (e: Edicion) => void; cargando: boolean; error: unknown;
}) {
  const [enun, setEnun] = useState(p.enunciado);
  const [ops, setOps] = useState(p.opciones);
  const [ok, setOk] = useState(p.correcta);
  const [expl, setExpl] = useState(p.explicacion ?? "");
  const campo = "w-full rounded-xl border border-line bg-bg px-3 py-2";
  const valido = enun.trim() && ops.every((o) => o.trim());
  return (
    <Dialogo titulo="Editar pregunta" onCerrar={onCerrar}>
      <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); onGuardar({ enunciado: enun.trim(), opciones: ops.map((o) => o.trim()), correcta: ok, explicacion: expl.trim() }); }}>
        <div><label htmlFor="enun" className="mb-1 block text-sm font-medium">Pregunta</label>
          <textarea id="enun" rows={2} className={campo} value={enun} onChange={(e) => setEnun(e.target.value)} /></div>
        <fieldset className="space-y-2"><legend className="mb-1 text-sm font-medium">Opciones (marca la correcta)</legend>
          {ops.map((o, i) => (
            <div key={i} className="flex items-center gap-2">
              <input type="radio" name="ok" checked={ok === i} onChange={() => setOk(i)} aria-label={`Opción ${i + 1} es la correcta`} className="h-5 w-5 accent-[#F5A31A]" />
              <input className={campo} value={o} aria-label={`Opción ${i + 1}`} onChange={(e) => setOps(ops.map((x, j) => (j === i ? e.target.value : x)))} />
            </div>
          ))}
        </fieldset>
        <div><label htmlFor="expl" className="mb-1 block text-sm font-medium">Explicación</label>
          <textarea id="expl" rows={2} className={campo} value={expl} onChange={(e) => setExpl(e.target.value)} /></div>
        {error != null && <ErrorCaja error={error} />}
        <div className="flex justify-end gap-2">
          <Button type="button" onClick={onCerrar}>Cancelar</Button>
          <Button type="submit" variante="primario" disabled={!valido || cargando}>Guardar y aprobar</Button>
        </div>
      </form>
    </Dialogo>
  );
}

function TarjetaPregunta({ p, onEstado, onEditar, ocupado, soloRetirar }: {
  p: PreguntaBanco; onEstado: (e: EstadoPregunta) => void; onEditar?: () => void; ocupado: boolean; soloRetirar?: boolean;
}) {
  const [confirmando, setConfirmando] = useState(false);
  const pct = p.puntaje_jev === null ? null : Math.round(p.puntaje_jev * 100);
  return (
    <Card className="rise space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <p className="text-lg font-semibold">{p.enunciado}</p>
        <div className="flex gap-2">
          <Badge nivel="ok">{p.tema}</Badge>
          {pct !== null && <Badge nivel={nivelJev(p.puntaje_jev)}>Calidad {pct}%</Badge>}
          {p.estado === "revisar" && <Badge nivel="warn">Por revisar</Badge>}
        </div>
      </div>
      <ol className="grid gap-2 sm:grid-cols-2">
        {p.opciones.map((o, i) => (
          <li key={i} className={cx("flex items-center gap-2 rounded-xl border px-3 py-2", i === p.correcta ? "border-ok bg-ok/15" : "border-line")}>
            <span className="font-bold">{i + 1}.</span><span className="flex-1">{o}</span>
            {i === p.correcta && <><Check size={16} className="text-ok" aria-hidden /><span className="sr-only">Respuesta correcta</span></>}
          </li>
        ))}
      </ol>
      {p.explicacion && <p className="text-sm"><span className="font-medium">Explicación: </span>{p.explicacion}</p>}
      <p className="text-sm text-muted">Fuente: {[p.documento, p.seccion].filter(Boolean).join(", ") || "sin fuente"}</p>
      {soloRetirar ? (
        <div className="flex flex-wrap items-center gap-2">
          {confirmando ? (
            <>
              <span className="text-sm">¿Seguro que quieres retirar esta pregunta? Ya no se usará en los exámenes.</span>
              <Button variante="peligro" disabled={ocupado} onClick={() => onEstado("retirada")}>Sí, retirar</Button>
              <Button disabled={ocupado} onClick={() => setConfirmando(false)}>No, dejarla</Button>
            </>
          ) : (
            <Button variante="peligro" disabled={ocupado} onClick={() => setConfirmando(true)}><Trash2 size={16} aria-hidden /> Retirar</Button>
          )}
        </div>
      ) : (
        <div className="flex flex-wrap gap-2">
          <Button variante="primario" disabled={ocupado} onClick={() => onEstado("aprobada")}><Check size={16} aria-hidden /> Aprobar</Button>
          <Button disabled={ocupado} onClick={onEditar}><Pencil size={16} aria-hidden /> Editar</Button>
          <Button variante="peligro" disabled={ocupado} onClick={() => onEstado("retirada")}><Trash2 size={16} aria-hidden /> Retirar</Button>
        </div>
      )}
    </Card>
  );
}

function PorAprobar() {
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["preguntas-por-aprobar"],
    queryFn: async () => {
      const [a, b] = await Promise.all([api.preguntas("pendiente"), api.preguntas("revisar")]);
      return [...a.preguntas, ...b.preguntas];
    },
  });
  const [editando, setEditando] = useState<PreguntaBanco | null>(null);
  const m = useMutation({
    mutationFn: (v: { id: number; estado: EstadoPregunta; editado?: Edicion }) => api.cambiarEstado(v.id, { estado: v.estado, editado: v.editado }),
    onSuccess: () => { setEditando(null); return qc.invalidateQueries({ queryKey: ["preguntas-por-aprobar"] }); },
  });
  if (q.error) return <ErrorCaja error={q.error} onReintentar={() => q.refetch()} />;
  if (!q.data) return <Cargando />;
  return (
    <>
      {m.error && !editando && <ErrorCaja error={m.error} />}
      {q.data.length === 0 ? <Vacio titulo="No hay preguntas esperando" texto="Cuando se generen preguntas nuevas, las verás aquí para aprobarlas." /> : (
        <div className="space-y-4">
          {q.data.map((p) => (
            <TarjetaPregunta key={p.id} p={p} ocupado={m.isPending} onEditar={() => { m.reset(); setEditando(p); }}
              onEstado={(estado) => m.mutate({ id: p.id, estado })} />
          ))}
        </div>
      )}
      {editando && <Editar p={editando} cargando={m.isPending} error={m.error} onCerrar={() => setEditando(null)}
        onGuardar={(editado) => m.mutate({ id: editando.id, estado: "aprobada", editado })} />}
    </>
  );
}

function Banco() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["preguntas-aprobadas"], queryFn: () => api.preguntas("aprobada") });
  const [tema, setTema] = useState("");
  const m = useMutation({
    mutationFn: (id: number) => api.cambiarEstado(id, { estado: "retirada" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["preguntas-aprobadas"] }),
  });
  if (q.error) return <ErrorCaja error={q.error} onReintentar={() => q.refetch()} />;
  if (!q.data) return <Cargando />;
  const todas = q.data.preguntas;
  const nombre = (p: PreguntaBanco) => p.documento ?? p.tema;
  const temas = [...new Set(todas.map(nombre))].sort();
  const lista = todas.filter((p) => !tema || nombre(p) === tema);
  return (
    <>
      <div className="flex flex-wrap items-center gap-3">
        <p className="font-medium" aria-live="polite">{lista.length} {lista.length === 1 ? "pregunta aprobada" : "preguntas aprobadas"}</p>
        <label className="sr-only" htmlFor="banco-tema">Filtrar por tema</label>
        <select id="banco-tema" value={tema} onChange={(e) => setTema(e.target.value)} className="rounded-xl border border-line bg-surface px-3 py-2">
          <option value="">Todos los temas</option>
          {temas.map((t) => <option key={t}>{t}</option>)}
        </select>
      </div>
      {m.error != null && <ErrorCaja error={m.error} />}
      {lista.length === 0 ? <Vacio titulo="No hay preguntas aprobadas" texto={tema ? "Prueba con otro tema." : "Cuando apruebes preguntas, quedarán guardadas aquí."} /> : (
        <div className="space-y-4">
          {lista.map((p) => <TarjetaPregunta key={p.id} p={p} soloRetirar ocupado={m.isPending} onEstado={() => m.mutate(p.id)} />)}
        </div>
      )}
    </>
  );
}

function Resultados() {
  const q = useQuery({ queryKey: ["reporte"], queryFn: api.reporte });
  if (q.error) return <ErrorCaja error={q.error} onReintentar={() => q.refetch()} />;
  if (!q.data) return <Cargando />;
  const { por_persona: pp, mas_falladas: mf } = q.data;
  return (
    <>
      {pp.length === 0 ? <Vacio titulo="Aún no hay evaluaciones" texto="Cuando tu equipo rinda una evaluación, las notas aparecerán aquí." /> : (
        <Tabla>
          <thead><tr><Th>Persona</Th><Th>Tema</Th><Th className="text-right">Intentos</Th><Th className="text-right">Mejor nota</Th><Th>Resultado</Th></tr></thead>
          <tbody>
            {pp.map((r) => (
              <tr key={`${r.id_empleado}-${r.tema}`}><Td className="font-medium">{r.nombre}</Td><Td>{r.tema}</Td>
                <Td className="text-right tabular-nums">{r.intentos}</Td><Td className="text-right tabular-nums">{r.mejor_nota}%</Td>
                <Td><Badge nivel={r.aprobado ? "ok" : "bad"}>{r.aprobado ? "Aprobado" : "No aprobado"}</Badge></Td></tr>
            ))}
          </tbody>
        </Tabla>
      )}
      <h2 className="text-lg font-semibold">Preguntas más falladas</h2>
      {mf.length === 0 ? <Vacio titulo="Sin fallos registrados" /> : (
        <Card><ul className="divide-y divide-line">
          {mf.map((f, i) => (
            <li key={i} className="flex items-start justify-between gap-3 py-3">
              <div><p className="font-medium">{f.enunciado}</p><p className="text-sm text-muted">{[f.documento, f.seccion].filter(Boolean).join(", ")}</p></div>
              <Badge nivel="bad">{f.fallos} {f.fallos === 1 ? "fallo" : "fallos"}</Badge>
            </li>
          ))}
        </ul></Card>
      )}
    </>
  );
}

export default function Panel() {
  const [tab, setTab] = useState<"aprobar" | "banco" | "resultados" | "analisis" | "cambios">("aprobar");
  return (
    <Pagina titulo="Panel del dueño" subtitulo="Revisa las preguntas y mira cómo le va a tu equipo.">
      <Pestanas valor={tab} onCambia={setTab} items={[{ id: "aprobar", nombre: "Preguntas por aprobar" }, { id: "banco", nombre: "Banco de preguntas" }, { id: "resultados", nombre: "Resultados" }, { id: "analisis", nombre: "Análisis" }, { id: "cambios", nombre: "Cambios" }]} />
      {tab === "aprobar" ? <PorAprobar /> : tab === "banco" ? <Banco /> : tab === "analisis" ? <Analisis /> : tab === "cambios" ? <Cambios /> : <Resultados />}
    </Pagina>
  );
}
