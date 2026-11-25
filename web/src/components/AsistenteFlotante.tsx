import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Check, Copy, Loader2, MessageCircle, RotateCw, Send, X } from "lucide-react";
import { abrirChat, cerrarChat, enviar, reintentar, useChat, type Mensaje } from "../lib/chatStore";
import { listaATabla } from "../lib/tabla";
import { Button, cx } from "./ui/ui";
import { Logo } from "./Logo";

const SUGERIDAS = [
  "¿Qué vence esta semana?",
  "¿Qué vence en diciembre?",
  "¿Cuánto cuesta la merma por caducidad?",
  "¿Cómo me lavo las manos según el manual?",
  "¿Qué hago si un cliente tiene alergia?",
];

function Copiar({ texto }: { texto: string }) {
  const [ok, setOk] = useState(false);
  return (
    <button aria-label="Copiar respuesta" className="rounded-lg p-1.5 text-muted hover:bg-line/50 hover:text-ink"
      onClick={() => { void navigator.clipboard?.writeText(texto).then(() => { setOk(true); setTimeout(() => setOk(false), 1500); }); }}>
      {ok ? <Check size={16} /> : <Copy size={16} />}
    </button>
  );
}

function Burbuja({ m }: { m: Mensaje }) {
  if (m.rol === "user")
    return <div className="rise ml-auto max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-sm bg-brand px-4 py-2.5 text-black">{m.texto}</div>;
  return (
    <div className={cx("rise max-w-[95%] rounded-2xl rounded-bl-sm border bg-surface px-4 py-3", m.error ? "border-warn/50" : "border-line")}>
      {m.error ? (
        <div className="space-y-2">
          <p>{m.texto}</p>
          <Button onClick={() => void reintentar(m)}><RotateCw size={14} aria-hidden /> Reintentar</Button>
        </div>
      ) : (
        <>
          <div className="md overflow-x-auto"><ReactMarkdown remarkPlugins={[remarkGfm]}>{listaATabla(m.texto)}</ReactMarkdown></div>
          <div className="mt-1 flex justify-end"><Copiar texto={m.texto} /></div>
        </>
      )}
    </div>
  );
}

/** Asistente en burbuja flotante: disponible en todas las pantallas. */
export function AsistenteFlotante() {
  const { mensajes, esperando, abierto } = useChat();
  const [texto, setTexto] = useState("");
  const fin = useRef<HTMLDivElement>(null);

  useEffect(() => { if (abierto) fin.current?.scrollIntoView({ block: "end" }); }, [mensajes, esperando, abierto]);
  useEffect(() => {
    if (!abierto) return;
    const alEscape = (e: KeyboardEvent) => { if (e.key === "Escape") cerrarChat(); };
    window.addEventListener("keydown", alEscape);
    return () => window.removeEventListener("keydown", alEscape);
  }, [abierto]);

  const mandar = (t: string) => { if (t.trim()) { void enviar(t); setTexto(""); } };

  return (
    <div className="no-print">
      {!abierto && (
        <button onClick={() => abrirChat()} aria-label="Abrir el asistente de ChefChat"
          className="fixed bottom-5 right-5 z-40 flex items-center gap-2 rounded-full bg-brand px-5 py-3.5 font-semibold text-black shadow-lg transition hover:brightness-110">
          <MessageCircle size={22} aria-hidden /> Pregúntale a ChefChat
          {esperando && <Loader2 size={16} className="animate-spin" aria-label="Buscando respuesta" />}
        </button>
      )}
      {abierto && (
        <section role="dialog" aria-label="Asistente de ChefChat"
          className="rise fixed inset-x-2 bottom-2 z-40 flex h-[min(42rem,calc(100vh-1.5rem))] flex-col overflow-hidden rounded-2xl border border-line bg-bg shadow-2xl sm:inset-x-auto sm:bottom-5 sm:right-5 sm:w-[26rem]">
          <header className="flex items-center gap-3 border-b border-line bg-surface px-4 py-3">
            <Logo size={28} />
            <div className="leading-tight">
              <p className="font-semibold">ChefChat</p>
              <p className="text-xs text-muted">Responde con los datos de tu restaurante</p>
            </div>
            <button onClick={cerrarChat} aria-label="Cerrar el asistente" className="ml-auto rounded-lg p-2 text-muted hover:bg-line/50 hover:text-ink"><X size={18} /></button>
          </header>
          <div className="flex-1 space-y-3 overflow-y-auto p-3" role="log" aria-live="polite" aria-label="Conversación">
            <div className="max-w-[95%] rounded-2xl border border-line bg-surface p-3 text-sm">
              Hola, soy ChefChat. Respondo con tus datos y cito los manuales. ¿Qué quieres saber?
            </div>
            <div className="flex flex-wrap gap-2" aria-label="Preguntas sugeridas">
              {SUGERIDAS.map((q) => (
                <button key={q} disabled={esperando} onClick={() => mandar(q)}
                  className="rounded-full border border-line px-3 py-1 text-left text-xs hover:border-brand hover:text-brand disabled:opacity-50">{q}</button>
              ))}
            </div>
            {mensajes.map((m) => <Burbuja key={m.id} m={m} />)}
            {esperando && (
              <div className="flex items-center gap-2 text-sm text-muted" role="status"><Loader2 className="animate-spin" size={16} aria-hidden /> ChefChat está buscando…</div>
            )}
            <div ref={fin} />
          </div>
          <form className="flex gap-2 border-t border-line bg-surface p-3" onSubmit={(e) => { e.preventDefault(); mandar(texto); }}>
            <label className="sr-only" htmlFor="msg">Escribe tu pregunta</label>
            <textarea id="msg" rows={1} value={texto} maxLength={2000} placeholder="Escribe tu pregunta…"
              onChange={(e) => setTexto(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); mandar(texto); } }}
              className="min-w-0 flex-1 resize-none rounded-xl border border-line bg-bg px-3 py-2" />
            <Button type="submit" variante="primario" disabled={esperando || !texto.trim()} aria-label="Enviar"><Send size={16} aria-hidden /></Button>
          </form>
        </section>
      )}
    </div>
  );
}
