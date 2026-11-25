import { useCallback, useEffect, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { BookOpen, ClipboardCheck, Clock } from "lucide-react";
import { api, type Intento, type Resultado } from "../lib/api";
import { Button, Card, Cargando, ErrorCaja, Pagina, cx } from "../components/ui/ui";
import { PreguntaExamen } from "../components/PreguntaExamen";

type Modo = "practica" | "evaluacion";
interface Feedback { correcta: boolean; respuesta_correcta: number; explicacion: string; fuente: string }

const reloj = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

function Configurar({ onIniciar, error, cargando }: { onIniciar: (e: string, t: string, m: Modo) => void; error: unknown; cargando: boolean }) {
  const trab = useQuery({ queryKey: ["trabajadores"], queryFn: api.trabajadores });
  const temas = useQuery({ queryKey: ["temas"], queryFn: api.temas });
  const [emp, setEmp] = useState("");
  const [tema, setTema] = useState("");
  const [modo, setModo] = useState<Modo | null>(null);
  const e = trab.error ?? temas.error;
  if (e) return <ErrorCaja error={e} onReintentar={() => { void trab.refetch(); void temas.refetch(); }} />;
  if (!trab.data || !temas.data) return <Cargando filas={3} />;
  const listo = emp && tema && modo;
  const campo = "w-full rounded-xl border border-line bg-surface px-3 py-2.5";
  const modos: { id: Modo; titulo: string; texto: string; Icono: typeof BookOpen }[] = [
    { id: "practica", titulo: "Práctica", texto: "Aprende sin presión, ves la respuesta al instante.", Icono: BookOpen },
    { id: "evaluacion", titulo: "Evaluación", texto: "Con tiempo y nota, cuenta para tu registro.", Icono: ClipboardCheck },
  ];
  return (
    <>
      <div className="grid gap-4 sm:grid-cols-2">
        <div><label htmlFor="emp" className="mb-1 block font-medium">¿Quién eres?</label>
          <select id="emp" className={campo} value={emp} onChange={(x) => setEmp(x.target.value)}>
            <option value="">Elige tu nombre</option>
            {trab.data.trabajadores.map((t) => <option key={t.id_empleado} value={t.id_empleado}>{t.nombre_completo}{t.cargo ? ` · ${t.cargo}` : ""}</option>)}
          </select></div>
        <div><label htmlFor="tema" className="mb-1 block font-medium">Tema</label>
          <select id="tema" className={campo} value={tema} onChange={(x) => setTema(x.target.value)}>
            <option value="">Elige un tema</option>
            {temas.data.temas.map((t) => <option key={t.tema} value={t.tema}>{t.tema} ({t.aprobadas ?? 0} preguntas)</option>)}
          </select></div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2" role="radiogroup" aria-label="Modo">
        {modos.map(({ id, titulo, texto, Icono }) => (
          <button key={id} role="radio" aria-checked={modo === id} onClick={() => setModo(id)}
            className={cx("rounded-2xl border p-6 text-left transition", modo === id ? "border-brand bg-brand/10" : "border-line bg-surface hover:border-brand")}>
            <Icono className="text-brand" aria-hidden />
            <p className="mt-3 text-xl font-bold">{titulo}</p>
            <p className="mt-1 text-muted">{texto}</p>
          </button>
        ))}
      </div>
      {error != null && <ErrorCaja error={error} />}
      <Button variante="primario" disabled={!listo || cargando} className="px-8 py-3 text-base"
        onClick={() => onIniciar(emp, tema, modo as Modo)}>Comenzar</Button>
    </>
  );
}

function Sesion({ intento, onTerminar }: { intento: Intento; onTerminar: (r: Resultado) => void }) {
  const [idx, setIdx] = useState(0);
  const [elegida, setElegida] = useState<number | null>(null);
  const [fb, setFb] = useState<Feedback | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [ocupado, setOcupado] = useState(false);
  const [restante, setRestante] = useState(intento.minutos ? intento.minutos * 60 : null);
  const fin = useRef(intento.minutos ? Date.now() + intento.minutos * 60_000 : 0);
  const cerrando = useRef(false);
  const eval_ = intento.modo === "evaluacion";
  const total = intento.preguntas.length;
  const p = intento.preguntas[idx];

  const cerrar = useCallback(async () => {
    if (cerrando.current) return;
    cerrando.current = true;
    try { onTerminar(await api.cerrar(intento.intento_id)); }
    catch (e) { cerrando.current = false; setError(e); }
  }, [intento.intento_id, onTerminar]);

  useEffect(() => {
    if (!eval_) return;
    const t = setInterval(() => {
      const s = Math.max(0, Math.round((fin.current - Date.now()) / 1000));
      setRestante(s);
      if (s === 0) { clearInterval(t); void cerrar(); }
    }, 500);
    return () => clearInterval(t);
  }, [eval_, cerrar]);

  const avanzar = () => {
    if (idx + 1 >= total) return void cerrar();
    setIdx(idx + 1); setElegida(null); setFb(null);
  };

  const elegir = useCallback(async (i: number) => {
    if (ocupado || elegida !== null || cerrando.current) return;
    setOcupado(true); setError(null); setElegida(i);
    try {
      const r = await api.responder(intento.intento_id, { pregunta_id: p.id, elegida: i });
      if ("correcta" in r) setFb(r);
      else { setOcupado(false); setElegida(null); avanzar(); return; }
    } catch (e) { setError(e); setElegida(null); }
    setOcupado(false);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ocupado, elegida, intento.intento_id, p, idx]);

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-4">
        <div className="flex-1">
          <p className="mb-1 text-sm font-medium" aria-live="polite">{idx + 1} de {total}</p>
          <div className="h-2.5 rounded-full bg-line" role="progressbar" aria-valuemin={0} aria-valuemax={total} aria-valuenow={idx + 1} aria-label="Progreso">
            <div className="h-2.5 rounded-full bg-brand transition-all" style={{ width: `${((idx + 1) / total) * 100}%` }} />
          </div>
        </div>
        {restante !== null && (
          <div className={cx("flex items-center gap-1.5 rounded-xl border px-3 py-1.5 font-mono text-lg tabular-nums", restante <= 60 ? "border-bad text-bad" : "border-line")} role="timer" aria-label={`Tiempo restante ${reloj(restante)}`}>
            <Clock size={16} aria-hidden /> {reloj(restante)}
          </div>
        )}
      </div>
      <PreguntaExamen pregunta={p} elegida={elegida} correcta={fb ? fb.respuesta_correcta : null} deshabilitada={ocupado || fb !== null} onElegir={(i) => void elegir(i)} />
      {error != null && <ErrorCaja error={error} />}
      {fb && (
        <Card className={cx("rise", fb.correcta ? "border-ok/50" : "border-bad/50")} role="status">
          <p className={cx("text-lg font-bold", fb.correcta ? "text-ok" : "text-bad")}>{fb.correcta ? "¡Correcto!" : "No es esa"}</p>
          {fb.explicacion && <p className="mt-1">{fb.explicacion}</p>}
          <p className="mt-2 text-sm text-muted">Fuente: {fb.fuente}</p>
          <Button variante="primario" className="mt-3" onClick={avanzar}>{idx + 1 >= total ? "Ver resultado" : "Siguiente"}</Button>
        </Card>
      )}
    </div>
  );
}

function Final({ r, modo, onOtra }: { r: Resultado; modo: Modo; onOtra: () => void }) {
  const ok = r.aprobado;
  return (
    <div className="space-y-5">
      <Card className="text-center">
        <p className={cx("text-7xl font-bold tabular-nums", ok === null ? "text-brand" : ok ? "text-ok" : "text-bad")}>{r.nota}%</p>
        <p className="mt-1 text-muted">{r.aciertos} de {r.total} correctas</p>
        <p className="mt-3 text-lg font-semibold">
          {modo === "practica" ? "Buen trabajo practicando. Esta práctica no cuenta para tu registro."
            : ok ? `¡Aprobaste con ${r.nota}%! Buen trabajo.`
              : `Sacaste ${r.nota}%. Necesitas ${r.nota_minima}%. Repasa estas secciones y vuelve a intentarlo.`}
        </p>
        {r.fuera_de_tiempo && <p className="mt-1 text-sm text-warn">Se acabó el tiempo.</p>}
      </Card>
      {r.falladas.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold">Para repasar</h2>
          {r.falladas.map((f, i) => (
            <Card key={i}>
              <p className="font-medium">{f.pregunta}</p>
              <p className="mt-1 text-sm">Respuesta correcta: <span className="text-ok">{f.respuesta_correcta}</span></p>
              {f.explicacion && <p className="mt-1 text-sm text-muted">{f.explicacion}</p>}
              <p className="mt-1 text-sm text-muted">Fuente: {f.fuente}</p>
            </Card>
          ))}
        </div>
      )}
      <Button variante="primario" onClick={onOtra}>Volver al inicio de capacitación</Button>
    </div>
  );
}

export default function Capacitacion() {
  const [intento, setIntento] = useState<Intento | null>(null);
  const [res, setRes] = useState<Resultado | null>(null);
  const [empezo, setEmpezo] = useState(false);
  const ini = useMutation({ mutationFn: (v: { e: string; t: string; m: Modo }) => api.iniciar({ id_empleado: v.e, tema: v.t, modo: v.m }), onSuccess: setIntento });
  const terminar = useCallback((r: Resultado) => setRes(r), []);
  const reset = () => { setIntento(null); setRes(null); setEmpezo(false); ini.reset(); };
  return (
    <Pagina titulo="Capacitación" subtitulo={!intento ? "Practica o rinde tu evaluación." : undefined}>
      {res && intento ? <Final r={res} modo={intento.modo} onOtra={reset} />
        : intento ? (
          <>
            {intento.modo === "evaluacion" && !empezo ? (
              <Card className="space-y-4 border-brand/50 text-center">
                <p className="text-xl font-semibold">Tienes {intento.minutos} minutos y {intento.preguntas.length} preguntas. No podrás volver atrás. ¿Empezamos?</p>
                <Button variante="primario" className="px-8 py-3 text-base" onClick={() => setEmpezo(true)}>Empezar</Button>
              </Card>
            ) : <Sesion intento={intento} onTerminar={terminar} />}
          </>
        ) : <Configurar cargando={ini.isPending} error={ini.error} onIniciar={(e, t, m) => ini.mutate({ e, t, m })} />}
    </Pagina>
  );
}

